"""アクションの状態遷移を管理するサービス"""

from battle.constants import GaugeStatus, BattlePhase
from battle.domain.utils import transition_to_phase

class ActionService:
    """ゲージのリセット、中断処理などの状態遷移ロジックを統合"""

    @staticmethod
    def reset_to_cooldown(gauge):
        """行動終了後、または非戦闘的な中断時にクールダウン状態へ移行する。"""
        gauge.status = GaugeStatus.COOLDOWN
        gauge.progress = 0.0
        gauge.selected_action = None
        gauge.selected_part = None

    @staticmethod
    def interrupt_action(world, entity_id: int, context, flow, message: str):
        """アクションを中断させ、進行度を反転させて強制的に冷却へ移行させる"""
        context.battle_log.append(message)
        transition_to_phase(flow, BattlePhase.LOG_WAIT)
        
        comps = world.try_get_entity(entity_id)
        if not comps or 'gauge' not in comps:
            return

        gauge = comps['gauge']
        
        # 中断ロジック：現在のチャージ進行度を冷却の残り時間に変換する
        current_p = gauge.progress
        gauge.status = GaugeStatus.COOLDOWN
        gauge.progress = max(0.0, 100.0 - current_p)
        gauge.selected_action = None
        gauge.selected_part = None
        
        # 待機列から自分を削除
        if entity_id in context.waiting_queue:
            context.waiting_queue.remove(entity_id)