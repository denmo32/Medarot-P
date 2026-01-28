"""バトルフロー管理システム"""

from core.ecs import System
from battle.constants import BattlePhase
from battle.domain.battle_helper import transition_to_phase, get_battle_state

class BattleFlowSystem(System):
    """
    バトル全体のフェーズ遷移を管理する。
    """
    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not context or not flow: return
        
        if flow.current_phase == BattlePhase.LOG_WAIT:
            if not context.battle_log:
                transition_to_phase(flow, BattlePhase.IDLE)