"""カットイン演出の時間軸・ステップ進行・描画状態計算を一元管理するディレクター。"""
import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

from domain.constants import AccentState, PartType, TeamType
from domain.models import ActionResult
from .cutin_timeline import (
    ActorMotion,
    CutinProfile,
    ImpactMotion,
    ProjectileMotion,
    resolve_cutin_profile,
)

if TYPE_CHECKING:
    from ..simulation.entities.commands import ExecutionReport
    from ..simulation.entities.part import Part
    from ..simulation.entities.robot import Robot
    from .visual_state import RobotVisualState


CUTIN_POPUP_LABELS = {
    "critical": "CRITICAL!!",
    "guard": "GUARD",
    "hit": "HIT!",
    "miss": "MISS!",
    "pierce": "PENETRATION",
}


@dataclass(frozen=True)
class CutinActorState:
    team: TeamType
    part_status: Dict[PartType, float]
    accent_state: AccentState
    is_visible: bool = True
    motion: Optional[ActorMotion] = None


@dataclass(frozen=True)
class CutinPopupState:
    primary_label: str
    damage_label: str
    is_miss: bool


@dataclass(frozen=True)
class CutinRenderState:
    actor: CutinActorState
    target: CutinActorState
    popup: Optional[CutinPopupState] = None
    projectiles: List[ProjectileMotion] = field(default_factory=list)
    impacts: List[ImpactMotion] = field(default_factory=list)
    camera_progress: Optional[float] = None


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

    def _resolve_popup(self) -> Optional[CutinPopupState]:
        result = self.result
        if result is None:
            return None

        if self.step == CutinStep.PIERCE:
            pierce = result.pierce_effect
            dmg = pierce.effective_damage if pierce else 0
            return CutinPopupState(
                primary_label=CUTIN_POPUP_LABELS["pierce"],
                damage_label=f"-{dmg}",
                is_miss=False,
            )

        if not result.success:
            return CutinPopupState(
                primary_label="",
                damage_label=CUTIN_POPUP_LABELS["miss"],
                is_miss=True,
            )

        if result.is_critical:
            label = CUTIN_POPUP_LABELS["critical"]
        elif result.is_guarded:
            label = CUTIN_POPUP_LABELS["guard"]
        else:
            label = CUTIN_POPUP_LABELS["hit"]

        return CutinPopupState(
            primary_label=label,
            damage_label=f"-{result.effective_damage}",
            is_miss=False,
        )

    def get_render_state(self, visual_states: Dict['Robot', 'RobotVisualState']) -> CutinRenderState:
        """現在の経過時間に応じた描画パラメータを算出（純粋計算・Pygame非依存）"""
        actor_vs = visual_states[self.actor]
        target_vs = visual_states[self.target]

        actor_state = CutinActorState(
            team=self.actor.team,
            part_status=actor_vs.parts_break_progress,
            accent_state=actor_vs.accent_state,
        )
        target_state = CutinActorState(
            team=self.target.team,
            part_status=target_vs.parts_break_progress,
            accent_state=target_vs.accent_state,
        )

        profile = self.profile
        elapsed = self.elapsed
        step = self.step
        result = self.result

        camera_progress: Optional[float] = None
        if profile.camera_track is not None:
            camera_progress = profile.camera_track.evaluate(elapsed)

        if step == CutinStep.PIERCE or self.is_result_shown:
            if profile.actor_movement is not None:
                actor_state = dataclasses.replace(actor_state, is_visible=False, motion=None)
            elif profile.camera_track is not None:
                camera_progress = 1.0
                actor_state = dataclasses.replace(actor_state, is_visible=False)

            return CutinRenderState(
                actor=actor_state,
                target=target_state,
                popup=self._resolve_popup(),
                projectiles=[],
                impacts=[],
                camera_progress=camera_progress,
            )

        is_hit = result.success if result else False

        if profile.actor_movement is not None:
            is_visible, motion = profile.actor_movement.evaluate(elapsed)
            actor_state = dataclasses.replace(actor_state, is_visible=is_visible, motion=motion)
        elif camera_progress is not None:
            is_visible = camera_progress < 1.0
            actor_state = dataclasses.replace(actor_state, is_visible=is_visible)

        projectiles = [
            p for track in profile.projectiles
            if (p := track.evaluate(elapsed, is_hit)) is not None
        ]
        impacts = [
            i for track in profile.impacts
            if (i := track.evaluate(elapsed, is_hit)) is not None
        ]

        show_popup = self.is_animation_finished or profile.popup.is_active(elapsed, is_hit)
        popup = self._resolve_popup() if show_popup else None

        return CutinRenderState(
            actor=actor_state,
            target=target_state,
            popup=popup,
            projectiles=projectiles,
            impacts=impacts,
            camera_progress=camera_progress,
        )