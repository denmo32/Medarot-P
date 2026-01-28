"""アクションの状態遷移を管理するサービス"""

from battle.constants import GaugeStatus, BattlePhase, ActionType
from battle.service.flow_service import transition_to_phase
from battle.logic.targeting import TargetingService
from battle.service.log_service import LogService

class ActionService:
    """ゲージのリセット、中断処理などの状態遷移・妥当性検証ロジックを統合"""

    @staticmethod
    def reset_to_cooldown(gauge):
        """行動終了後、または非戦闘的な中断時に放熱状態へ移行する。"""
        gauge.status = GaugeStatus.COOLDOWN
        gauge.progress = 0.0
        gauge.selected_action = None
        gauge.selected_part = None

    @staticmethod
    def validate_action_continuity(world, entity_id: int, context, flow) -> bool:
        """
        アクションの継続妥当性を検証するハンドラ。
        中断が必要な場合は中断処理を実行し、Falseを返す。
        """
        comps = world.try_get_entity(entity_id)
        if not comps or 'gauge' not in comps:
            return True

        gauge = comps['gauge']
        if gauge.status != GaugeStatus.CHARGING:
            return True

        actor_name = comps['medal'].nickname
        
        # 1. 予約パーツ自身の破壊チェック
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            if not TargetingService.is_action_target_valid(world, entity_id, gauge.selected_part):
                message = LogService.get_part_broken_interruption(actor_name)
                ActionService.interrupt_action(world, entity_id, context, flow, message)
                return False

        # 2. ターゲットロストチェック
        target_data = gauge.part_targets.get(gauge.selected_part)
        if target_data:
            target_id, target_part_type = target_data
            if not TargetingService.is_action_target_valid(world, target_id, target_part_type):
                message = LogService.get_target_lost(actor_name)
                ActionService.interrupt_action(world, entity_id, context, flow, message)
                return False
        
        return True

    @staticmethod
    def handle_target_loss(world, entity_id: int, context, flow):
        """
        ターゲットが消失（または解決不能）になった際の中断処理。
        """
        comps = world.try_get_entity(entity_id)
        if not comps: return
        
        actor_name = comps['medal'].nickname
        message = LogService.get_target_lost(actor_name)
        
        ActionService.interrupt_action(world, entity_id, context, flow, message)

    @staticmethod
    def interrupt_action(world, entity_id: int, context, flow, message: str):
        """アクションを中断させ、進行度を反転させて強制的に放熱へ移行させる"""
        context.battle_log.append(message)
        transition_to_phase(flow, BattlePhase.LOG_WAIT)
        
        comps = world.try_get_entity(entity_id)
        if not comps or 'gauge' not in comps:
            return

        gauge = comps['gauge']
        
        # 中断ロジック：現在の充填進行度を放熱の残り時間に変換する
        current_p = gauge.progress
        gauge.status = GaugeStatus.COOLDOWN
        gauge.progress = max(0.0, 100.0 - current_p)
        gauge.selected_action = None
        gauge.selected_part = None
        
        # 待機列から自分を削除
        if entity_id in context.waiting_queue:
            context.waiting_queue.remove(entity_id)