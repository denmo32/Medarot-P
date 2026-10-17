"""カットイン演出の時間軸・ステップ進行を一元管理するディレクター。"""
from enum import Enum, auto
from typing import List, Optional, TYPE_CHECKING

from domain.models import ActionResult
from ..constants import CutinStep
from .cutin_timeline import CutinProfile, resolve_cutin_profile

if TYPE_CHECKING:
    from ..models import Part


class CutinEvent(Enum):
    """カットイン演出のライフサイクルイベント"""
    ANIMATION_FINISHED = auto()
    PIERCE_ADVANCED = auto()
    COMPLETED = auto()


class CutinDirector:
    """カットイン演出の進行状態を管理するディレクター（表示モデル生成はプレゼンテーション層に委任）。"""

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
    def profile(self) -> CutinProfile:
        return self._profile

    @property
    def result(self) -> ActionResult:
        return self._result

    @property
    def has_pierce(self) -> bool:
        return self._has_pierce

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