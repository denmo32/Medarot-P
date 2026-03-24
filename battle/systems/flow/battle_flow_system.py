"""バトルフロー管理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.flow import FlowMechanics, PhaseTransition


class BattleFlowSystem(BattleSystemBase):
    """バトルフェーズの遷移管理"""

    def update(self, dt: float):
        context = self.context
        flow = self.flow

        if not context or not flow:
            return

        if flow.current_phase == BattlePhase.LOG_WAIT:
            if not context.battle_log:
                FlowMechanics.apply_transition(self.world, PhaseTransition(next_phase=BattlePhase.IDLE))
