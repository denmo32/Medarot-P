"""カットイン演出の時間軸・ステップ進行を一元管理するディレクター。"""
from enum import Enum
from typing import Optional, TYPE_CHECKING

from domain.models import ActionResult
from .cutin_timeline import CutinProfile, resolve_cutin_profile

if TYPE_CHECKING:
    from ..entities.commands import ExecutionReport
    from ..entities.part import Part
    from ..entities.robot import Robot


class CutinStep(str, Enum):
    """カットイン演出のステップ（第1段階：主攻撃、第2段階：貫通）"""
    PRIMARY = "primary"
    PIERCE = "pierce"


class CutinDirector:
    """カットイン演出の進行状態を管理するディレクター。
    攻撃者・対象・技情報および確定済みレポートをカプセル化します。
    """

    def __init__(
        self,
        actor: 'Robot',
        target: 'Robot',
        part: Optional['Part'],
        report: 'ExecutionReport',
    ):
        self.actor = actor
        self.target = target
        self.part = part
        self.report = report

        self.profile: CutinProfile = resolve_cutin_profile(part)
        self.duration: float = max(0.001, self.profile.duration)

        self.step: CutinStep = CutinStep.PRIMARY
        self.elapsed: float = 0.0
        self.is_result_shown: bool = False

    @property
    def result(self) -> Optional[ActionResult]:
        return self.report.result

    @property
    def has_pierce(self) -> bool:
        return self.report.has_pierce

    @property
    def is_animation_finished(self) -> bool:
        return self.elapsed >= self.duration

    def is_combatant(self, robot: 'Robot') -> bool:
        """指定機体がこのカットインの戦闘当事者（攻撃側または防御側）か"""
        return robot is self.actor or robot is self.target

    def update(self, dt: float):
        """アニメーション時間を進行させる"""
        if not self.is_result_shown and not self.is_animation_finished:
            self.elapsed = min(self.duration, self.elapsed + dt)

        if self.is_animation_finished:
            self.show_result()

    def advance(self):
        """演出を次の段階へ早送り・前進させる"""
        if not self.is_animation_finished:
            self.elapsed = self.duration
            self.show_result()
            return

        if self.step == CutinStep.PRIMARY and self.has_pierce:
            self.step = CutinStep.PIERCE
            self.show_result()

    def show_result(self):
        self.is_result_shown = True