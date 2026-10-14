"""カットイン演出の時間軸・ステップ進行・表示モデル生成を一元管理するディレクター。"""
import dataclasses
from enum import Enum, auto
from typing import List, Optional, TYPE_CHECKING

from domain.models import ActionResult
from features.battle.constants import CutinStep
from features.battle.cutin_timeline import (
    CutinProfile,
    resolve_cutin_popup,
    resolve_cutin_profile,
)
from features.battle.view_models import (
    CutinActorModel,
    CutinModel,
)

if TYPE_CHECKING:
    from features.battle.models import Part


class CutinEvent(Enum):
    """カットイン演出のライフサイクルイベント"""
    ANIMATION_FINISHED = auto()  # 飛翔・着弾アニメーション終了（結果適用契機）
    PIERCE_ADVANCED = auto()     # 貫通ステップへ進んだ
    COMPLETED = auto()           # カットイン全体の終了


class CutinDirector:
    """カットイン演出の進行と描画モデルの構築を一元管理するディレクター。

    アニメーション時間の管理、飛翔体・着弾エフェクトの評価、
    ポップアップ内容の決定、および貫通（PIERCE）ステップへの遷移を担う。
    """

    def __init__(
        self,
        profile: CutinProfile,
        result: ActionResult,
        has_pierce: bool,
        duration: Optional[float] = None,
    ):
        self._profile = profile
        self._result = result
        self._has_pierce = has_pierce
        self._duration = max(0.001, duration if duration is not None else profile.duration)

        self._step = CutinStep.PRIMARY
        self._elapsed = 0.0
        self._is_result_shown = False
        self._anim_finished_dispatched = False

    @classmethod
    def create(
        cls,
        part: Optional['Part'],
        result: ActionResult,
        has_pierce: bool,
    ) -> 'CutinDirector':
        """使用パーツから演出プロファイルと再生時間を自動解決してディレクターを生成する。"""
        profile = resolve_cutin_profile(part)
        return cls(profile=profile, result=result, has_pierce=has_pierce, duration=profile.duration)

    @property
    def step(self) -> CutinStep:
        return self._step

    @property
    def is_animation_finished(self) -> bool:
        """アニメーション（飛翔〜着弾）が完了したか"""
        return self._elapsed >= self._duration

    def update(self, dt: float) -> List[CutinEvent]:
        """アニメーションの経過時間を進め、完了時に ANIMATION_FINISHED イベントを返す"""
        events: List[CutinEvent] = []
        if not self._is_result_shown and not self.is_animation_finished:
            self._elapsed = min(self._duration, self._elapsed + dt)

        if self.is_animation_finished and not self._anim_finished_dispatched:
            self._anim_finished_dispatched = True
            self.show_result()
            events.append(CutinEvent.ANIMATION_FINISHED)

        return events

    def advance(self) -> List[CutinEvent]:
        """進行入力（キー押下など）を受け取り、演出ステップ遷移イベントを返す"""
        # アニメーション再生中のスキップ要求
        if not self.is_animation_finished:
            self._elapsed = self._duration
            self._anim_finished_dispatched = True
            self.show_result()
            return [CutinEvent.ANIMATION_FINISHED]

        # 結果表示中：貫通ステップへの遷移
        if self._step == CutinStep.PRIMARY and self._has_pierce:
            self._step = CutinStep.PIERCE
            self._is_result_shown = True
            return [CutinEvent.PIERCE_ADVANCED]

        # 演出終了
        return [CutinEvent.COMPLETED]

    def show_result(self):
        """アニメーション終了後の結果表示状態に移行する"""
        self._is_result_shown = True

    def update_final_result(self, result: ActionResult):
        """世界状態へ反映・確定された最終 ActionResult を同期する"""
        self._result = result

    def build_cutin_model(
        self,
        actor_model: CutinActorModel,
        target_model: CutinActorModel,
    ) -> CutinModel:
        """現在の演出状態に基づく CutinModel を構築する（副作用のない純粋クエリ）"""
        if self._step == CutinStep.PIERCE or self._is_result_shown:
            if self._profile.actor_movement is not None:
                actor_model = dataclasses.replace(actor_model, is_visible=False, motion=None)
            return CutinModel(
                actor=actor_model,
                target=target_model,
                popup=resolve_cutin_popup(self._result, self._step),
                projectiles=[],
                impacts=[],
            )

        is_hit = self._result.success
        elapsed = self._elapsed

        if self._profile.actor_movement is not None:
            is_visible, motion = self._profile.actor_movement.evaluate(elapsed)
            actor_model = dataclasses.replace(actor_model, is_visible=is_visible, motion=motion)

        projectiles = [
            p for track in self._profile.projectiles
            if (p := track.evaluate(elapsed, is_hit)) is not None
        ]
        impacts = [
            i for track in self._profile.impacts
            if (i := track.evaluate(elapsed, is_hit)) is not None
        ]

        show_popup = self.is_animation_finished or self._profile.popup.is_active(elapsed, is_hit)
        popup = resolve_cutin_popup(self._result, self._step) if show_popup else None

        return CutinModel(
            actor=actor_model,
            target=target_model,
            popup=popup,
            projectiles=projectiles,
            impacts=impacts,
        )