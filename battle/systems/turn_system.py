"""ターン開始管理システム"""

from core.ecs import System
from battle.ai.strategy import get_strategy
from battle.utils import calculate_action_times
from components.battle_flow import BattleFlowComponent
from battle.constants import TeamType, GaugeStatus, BattlePhase, ActionType

class TurnSystem(System):
    """
    IDLEフェーズにおいて待機列の先頭を確認し、
    プレイヤーならINPUTフェーズへ遷移、エネミーならAI意思決定を行ってチャージを開始する。
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
            if team.team_type == TeamType.PLAYER:
                # プレイヤー：入力待ちフェーズへ遷移
                context.current_turn_entity_id = eid
                flow.current_phase = BattlePhase.INPUT
            else:
                # エネミー：AIによる意思決定（フェーズ遷移はせず、チャージ状態にしてキューから外す）
                self._execute_ai_decision(eid, gauge, comps, context)

    def _execute_ai_decision(self, eid, gauge, comps, context):
        """エネミーAIの意思決定ロジック"""
        strategy = get_strategy("random")
        action, part = strategy.decide_action(self.world, eid)
        
        gauge.selected_action = action
        gauge.selected_part = part
        
        if action == ActionType.ATTACK and part:
            part_id = comps['partlist'].parts.get(part)
            part_comps = self.world.entities[part_id]
            attack_comp = part_comps.get('attack')
            
            if attack_comp:
                c_t, cd_t = calculate_action_times(attack_comp.attack)
                gauge.charging_time = c_t
                gauge.cooldown_time = cd_t
                
                # 属性ボーナス（時間短縮）の適用
                # メダルとパーツの属性が一致した場合、チャージ・クールダウン時間を5%短縮
                medal_comp = comps.get('medal')
                part_comp = part_comps.get('part')
                
                if medal_comp and part_comp:
                    if medal_comp.attribute != "undefined" and medal_comp.attribute == part_comp.attribute:
                        gauge.charging_time *= 0.95
                        gauge.cooldown_time *= 0.95

        # チャージフェーズへ移行させ、キューから外す
        gauge.status = GaugeStatus.CHARGING
        gauge.progress = 0.0
        if context.waiting_queue and context.waiting_queue[0] == eid:
            context.waiting_queue.pop(0)