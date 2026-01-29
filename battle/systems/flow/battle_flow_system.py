"""バトルフロー管理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.flow import transition_to_phase

class BattleFlowSystem(BattleSystemBase):
    def update(self, dt: float):
        context, flow = self.battle_state
        if not context or not flow: return
        
        if flow.current_phase == BattlePhase.LOG_WAIT:
            if not context.battle_log:
                transition_to_phase(flow, BattlePhase.IDLE)