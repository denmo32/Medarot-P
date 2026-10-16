"""バトルの演出進行（HPアニメーション、タイマー、カットイン）を一元管理するプレゼンテーション層。"""
from typing import Dict, List, Optional, Sequence, TYPE_CHECKING

from features.battle.constants import ADVANCEABLE_PHASES, BattlePhase
from .cutin_director import CutinDirector, CutinEvent
from .visual_damage import build_damage_visual_steps
from .visual_state import RobotVisualState

if TYPE_CHECKING:
    from domain.models import ActionResult
    from features.battle.commands import ExecutionReport
    from features.battle.models import Part, Robot


class BattlePresentation:
    """戦闘の視覚演出（HP変動アニメーション・演出待機タイマー・カットイン）を一元管理する。

    BattleManager や BattleContext から表示・演出の低レベルな関心事を完全に切り離し、
    自立した表示状態（VisualState, PhaseTimer, CutinDirector）を保持する。
    """

    def __init__(self, robots: Sequence['Robot']):
        self.visual_states: Dict['Robot', RobotVisualState] = {
            r: RobotVisualState(r) for r in robots
        }
        self.phase_timer: float = 0.0
        self.cutin_director: Optional[CutinDirector] = None

    # === タイマー管理 ===

    def start_phase_timer(self, duration: float):
        self.phase_timer = max(0.0, duration)

    def is_timer_active(self) -> bool:
        return self.phase_timer > 0.0

    def is_timer_expired(self) -> bool:
        return self.phase_timer <= 0.0

    # === HP アニメーション・待機判定 ===

    def is_hp_animating(self) -> bool:
        return any(vs.is_hp_animating for vs in self.visual_states.values())

    def is_busy(self) -> bool:
        return self.is_hp_animating() or self.is_timer_active()

    def is_waiting_for_advance(self, phase: BattlePhase) -> bool:
        if self.is_busy():
            return False
        return phase in ADVANCEABLE_PHASES

    # === フレーム更新 ===

    def update(self, dt: float):
        for vs in self.visual_states.values():
            vs.update(dt)

        if self.phase_timer > 0.0:
            self.phase_timer = max(0.0, self.phase_timer - dt)

    # === ダメージ演出のステージング ===

    def stage_damage(self, report: 'ExecutionReport'):
        if report and report.target:
            steps = build_damage_visual_steps(report)
            if steps:
                self.visual_states[report.target].stage_damage_steps(steps)

    def advance_damage_step(self, target: 'Robot'):
        if target in self.visual_states:
            self.visual_states[target].advance_damage_step()

    def sync_all_targets(self):
        for vs in self.visual_states.values():
            vs.sync_all_targets()
        self.phase_timer = 0.0

    # === カットイン演出のライフサイクル ===

    def start_cutin(self, part: Optional['Part'], report: 'ExecutionReport') -> CutinDirector:
        result = report.result
        has_pierce = report.has_pierce
        self.cutin_director = CutinDirector.create(part=part, result=result, has_pierce=has_pierce)
        return self.cutin_director

    def update_cutin(self, dt: float) -> List[CutinEvent]:
        if self.cutin_director:
            return self.cutin_director.update(dt)
        return []

    def advance_cutin(self) -> List[CutinEvent]:
        if self.cutin_director:
            return self.cutin_director.advance()
        return [CutinEvent.COMPLETED]

    def update_cutin_result(self, result: 'ActionResult'):
        if self.cutin_director:
            self.cutin_director.update_final_result(result)

    def clear_cutin(self):
        self.cutin_director = None