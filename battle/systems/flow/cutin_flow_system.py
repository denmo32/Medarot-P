"""カットイン演出のフロー制御システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase, BattleTiming
from battle.mechanics.flow import FlowMechanics, PhaseTransition


class CutinFlowSystem(BattleSystemBase):
    """カットイン演出の進行管理"""

    def update(self, dt: float):
        flow = self.flow
        if not flow or flow.current_phase != BattlePhase.CUTIN:
            return

        flow.phase_timer -= dt
        max_time = BattleTiming.CUTIN_ANIMATION
        elapsed = max(0.0, max_time - flow.phase_timer)
        flow.cutin_progress = min(1.0, elapsed / max_time)

        if flow.phase_timer <= 0:
            FlowMechanics.apply_transition(self.world, PhaseTransition(next_phase=BattlePhase.EXECUTING))
            flow.cutin_progress = 1.0
