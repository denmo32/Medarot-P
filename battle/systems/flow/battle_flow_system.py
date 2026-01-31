"""バトルフロー管理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase

class BattleFlowSystem(BattleSystemBase):
    def update(self, dt: float):
        context, flow = self.battle_state
        if not context or not flow: return
        
        if flow.current_phase == BattlePhase.LOG_WAIT:
            if not context.battle_log:
                self.change_phase(BattlePhase.IDLE)