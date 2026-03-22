"""バトルフロー管理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase

class BattleFlowSystem(BattleSystemBase):
    """バトルフェーズの遷移管理"""

    def update(self, dt: float):
        context = self.state.context
        flow = self.state.flow
        
        if not context or not flow:
            return

        if flow.current_phase == BattlePhase.LOG_WAIT:
            if not context.battle_log:
                self.state.change_phase(BattlePhase.IDLE)
