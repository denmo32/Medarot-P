"""バトルフロー管理システム"""

from core.ecs import System
from components.battle_flow import BattleFlowComponent
from battle.constants import BattlePhase
from battle.domain.utils import transition_to_phase

class BattleFlowSystem(System):
    """
    バトル全体のフェーズ遷移を管理する。
    """

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        
        eid, comps = entities[0]
        context = comps['battlecontext']
        flow = comps['battleflow']
        
        # ログ待ち状態でログが空になったらIDLEに戻る
        if flow.current_phase == BattlePhase.LOG_WAIT:
            if not context.battle_log:
                transition_to_phase(flow, BattlePhase.IDLE)