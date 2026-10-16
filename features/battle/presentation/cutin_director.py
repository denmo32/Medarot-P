"""カットイン演出の時間軸・ステップ進行・表示モデル生成を一元管理するディレクター。"""
import dataclasses
from enum import Enum, auto
from typing import List, Optional, TYPE_CHECKING

from domain.models import ActionResult
from features.battle.constants import CutinStep
from .cutin_timeline import (
    CutinProfile,
    resolve_cutin_popup,
    resolve_cutin_profile,
)
from .view_models import (
    CutinActorModel,
    CutinModel,
)

if TYPE_CHECKING:
    from features.battle.models import Part


class CutinEvent(Enum):
    """カットイン演出のライフサイクルイベント"""
    ANIMATION_FINISHED = auto()
    PIERCE_ADVANCED = auto()
    COMPLETED = auto()


class CutinDirector:
    """カットイン演出の進行と描画モデルの構築を一元管理するディレクター。"""

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
        profile = resolve_cutin_profile(part)
        return cls(profile=profile, result=result, has_pierce=has_pierce, duration=profile.duration)

    @property
    def step(self) -> CutinStep:
        return self._step

    @property
    def is_animation_finished(self) -> bool:
        return self._elapsed >= self._duration

    def update(self, dt: float) -> List[CutinEvent]:
        events: List[CutinEvent] = []
        if not self._is_result_shown and not self.is_animation_finished:
            self._elapsed = min(self._duration, self._elapsed + dt)

        if self.is_animation_finished and not self._anim_finished_dispatched:
            self._anim_finished_dispatched = True
            self.show_result()
            events.append(CutinEvent.ANIMATION_FINISHED)

        return events

    def advance(self) -> List[CutinEvent]:
        if not self.is_animation_finished:
            self._elapsed = self._duration
            self._anim_finished_dispatched = True
            self.show_result()
            return [CutinEvent.ANIMATION_FINISHED]

        if self._step == CutinStep.PRIMARY and self._has_pierce:
            self._step = CutinStep.PIERCE
            self._is_result_shown = True
            return [CutinEvent.PIERCE_ADVANCED]

        return [CutinEvent.COMPLETED]

    def show_result(self):
        self._is_result_shown = True

    def update_final_result(self, result: ActionResult):
        self._result = result

    def build_cutin_model(
        self,
        actor_model: CutinActorModel,
        target_model: CutinActorModel,
    ) -> CutinModel:
        camera_progress: Optional[float] = None
        if self._profile.camera_track is not None:
            camera_progress = self._profile.camera_track.evaluate(self._elapsed)

        if self._step == CutinStep.PIERCE or self._is_result_shown:
            if self._profile.actor_movement is not None:
                actor_model = dataclasses.replace(actor_model, is_visible=False, motion=None)
            elif self._profile.camera_track is not None:
                camera_progress = 1.0
                actor_model = dataclasses.replace(actor_model, is_visible=False)

            return CutinModel(
                actor=actor_model,
                target=target_model,
                popup=resolve_cutin_popup(self._result, self._step),
                projectiles=[],
                impacts=[],
                camera_progress=camera_progress,
            )

        is_hit = self._result.success
        elapsed = self._elapsed

        if self._profile.actor_movement is not None:
            is_visible, motion = self._profile.actor_movement.evaluate(elapsed)
            actor_model = dataclasses.replace(actor_model, is_visible=is_visible, motion=motion)
        elif camera_progress is not None:
            is_visible = camera_progress < 1.0
            actor_model = dataclasses.replace(actor_model, is_visible=is_visible)

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
            camera_progress=camera_progress,
        )