"""バトルフロー管理システム"""

from core.ecs import System
from components.battle_flow import BattleFlowComponent
from battle.constants import BattlePhase

class BattleFlowSystem(System):
    """
    バトル全体のフェーズ遷移を管理する。
    現状は主にログ待ちからIDLEへの復帰などを担当。
    """

    def update(self, dt: float):
        # コンテキストとフローの取得
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        
        eid, comps = entities[0]
        context = comps['battlecontext']
        flow = comps['battleflow']
        
        # ログ待ち状態でログが空になったらIDLEに戻る
        # (入力処理はInputSystemが行い、ログ送りをする。ここでは結果としての状態遷移を行う)
        if flow.current_phase == BattlePhase.LOG_WAIT:
            if not context.battle_log:
                flow.current_phase = BattlePhase.IDLE
                flow.processing_event_id = None
