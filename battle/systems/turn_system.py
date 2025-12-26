"""ターン開始管理システム"""

from core.ecs import System
from battle.ai.strategy import get_strategy
from battle.utils import calculate_action_times

class TurnSystem(System):
    """待機キューの先頭を確認し、プレイヤーなら入力待ち、エネミーならAI意思決定を開始する"""

    def update(self, dt: float):
        contexts = self.world.get_entities_with_components('battlecontext')
        if not contexts: return
        context = contexts[0][1]['battlecontext']

        # 他のイベント処理中はターンを開始しない
        if context.waiting_for_input or context.waiting_for_action or context.game_over:
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
        if gauge.status == gauge.ACTION_CHOICE:
            if team.team_type == "player":
                # プレイヤー：入力待ち状態へ遷移
                context.current_turn_entity_id = eid
                context.waiting_for_action = True
            else:
                # エネミー：AIによる意思決定
                self._execute_ai_decision(eid, gauge, comps, context)

    def _execute_ai_decision(self, eid, gauge, comps, context):
        """エネミーAIの意思決定ロジック"""
        strategy = get_strategy("random")
        action, part = strategy.decide_action(self.world, eid)
        
        gauge.selected_action = action
        gauge.selected_part = part
        
        if action == "attack" and part:
            part_id = comps['partlist'].parts.get(part)
            attack_comp = self.world.entities[part_id].get('attack')
            if attack_comp:
                c_t, cd_t = calculate_action_times(attack_comp.attack)
                gauge.charging_time = c_t
                gauge.cooldown_time = cd_t

        # チャージフェーズへ移行させ、キューから外す
        gauge.status = gauge.CHARGING
        gauge.progress = 0.0
        if context.waiting_queue and context.waiting_queue[0] == eid:
            context.waiting_queue.pop(0)