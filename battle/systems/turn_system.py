"""ターン開始管理システム"""

from core.ecs import System
from components.battle_flow import BattleFlowComponent
from battle.constants import TeamType, GaugeStatus, BattlePhase

class TurnSystem(System):
    """
    IDLEフェーズにおいて待機列の先頭を確認し、
    プレイヤーならINPUTフェーズへ、エネミーならENEMY_TURNフェーズへ遷移させる。
    意思決定ロジックはここには持たない。
    """

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        # IDLEフェーズ以外ではターン処理を行わない
        if flow.current_phase != BattlePhase.IDLE:
            return

        if not context.waiting_queue: return
        
        # キュー先頭のエンティティを取得
        eid = context.waiting_queue[0]
        comps = self.world.entities.get(eid)
        if not comps:
            context.waiting_queue.pop(0)
            return

        gauge = comps['gauge']
        team = comps['team']

        # 行動選択待ち（ACTION_CHOICE）状態のエンティティがキュー先頭に来た場合
        if gauge.status == GaugeStatus.ACTION_CHOICE:
            context.current_turn_entity_id = eid
            
            if team.team_type == TeamType.PLAYER:
                # プレイヤー：入力待ちフェーズへ遷移
                flow.current_phase = BattlePhase.INPUT
            else:
                # エネミー：AI思考フェーズへ遷移（AISystemが処理を行う）
                flow.current_phase = BattlePhase.ENEMY_TURN