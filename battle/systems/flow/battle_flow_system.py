"""バトルフロー管理システム"""

from core.ecs import System
from battle.constants import BattlePhase
from battle.mechanics.flow import transition_to_phase, get_battle_state

class BattleFlowSystem(System):
    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not context or not flow: return
        
        if flow.current_phase == BattlePhase.LOG_WAIT:
            if not context.battle_log:
                transition_to_phase(flow, BattlePhase.IDLE)