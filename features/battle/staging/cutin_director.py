"""カットイン演出の時間軸・ステップ進行を一元管理するディレクター。"""
from enum import Enum
from typing import Optional, TYPE_CHECKING

from domain.models import ActionResult
from .cutin_timeline import CutinProfile, resolve_cutin_profile

if TYPE_CHECKING:
    from ..entities.part import Part


class CutinStep(str, Enum):
    """カットイン演出のステップ（第1段階：主攻撃、第2段階：貫通）"""
    PRIMARY = "primary"
    PIERCE = "pierce"


class CutinDirector:
    """カットイン演出の進行状態を管理するディレクター（表示モデル生成はプレゼンテーション層に委任）。"""

    def __init__(
        self,
        profile: CutinProfile,
        result: ActionResult,
        duration: Optional[float] = None,
    ):
        self._profile = profile
        self._result = result
        self._duration = max(0.001, duration if duration is not None else profile.duration)

        self._step = CutinStep.PRIMARY
        self._elapsed = 0.0
        self._is_result_shown = False

    @classmethod
    def create(
        cls,
        part: Optional['Part'],
        result: ActionResult,
    ) -> 'CutinDirector':
        profile = resolve_cutin_profile(part)
        return cls(profile=profile, result=result, duration=profile.duration)

    @property
    def profile(self) -> CutinProfile:
        return self._profile

    @property
    def result(self) -> ActionResult:
        return self._result

    @property
    def has_pierce(self) -> bool:
        """結果データから貫通の有無を動的に導出（確定後の更新にも完全追従）"""
        return self._result.has_pierce

    @property
    def step(self) -> CutinStep:
        return self._step

    @property
    def elapsed(self) -> float:
        return self._elapsed

    @property
    def is_result_shown(self) -> bool:
        return self._is_result_shown

    @property
    def is_animation_finished(self) -> bool:
        return self._elapsed >= self._duration

    def update(self, dt: float):
        """アニメーション時間を進行させる"""
        if not self._is_result_shown and not self.is_animation_finished:
            self._elapsed = min(self._duration, self._elapsed + dt)

        if self.is_animation_finished:
            self.show_result()

    def advance(self):
        """演出を次の段階へ早送り・前進させる"""
        if not self.is_animation_finished:
            self._elapsed = self._duration
            self.show_result()
            return

        if self._step == CutinStep.PRIMARY and self.has_pierce:
            self._step = CutinStep.PIERCE
            self.show_result()

    def show_result(self):
        self._is_result_shown = True

    def update_final_result(self, result: ActionResult):
        self._result = result