"""アクションの状態遷移・妥当性検証ロジック（旧 ActionService）"""

from domain.constants import GaugeStatus, ActionType
from battle.constants import BattlePhase
from battle.mechanics.flow import transition_to_phase
from battle.mechanics.targeting import TargetingMechanics
from battle.mechanics.log import LogBuilder

class ActionMechanics:
    """ゲージのリセット、中断処理などのロジック"""

    @staticmethod
    def reset_to_cooldown(gauge):
        gauge.status = GaugeStatus.COOLDOWN
        gauge.progress = 0.0
        gauge.selected_action = None
        gauge.selected_part = None

    @staticmethod
    def validate_action_continuity(world, entity_id: int, context, flow) -> bool:
        """アクションの継続妥当性を検証"""
        comps = world.try_get_entity(entity_id)
        if not comps or 'gauge' not in comps: return True

        gauge = comps['gauge']
        if gauge.status != GaugeStatus.CHARGING: return True

        actor_name = comps['medal'].nickname
        
        # 1. パーツ破壊チェック
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            if not TargetingMechanics.is_action_target_valid(world, entity_id, gauge.selected_part):
                message = LogBuilder.get_part_broken_interruption(actor_name)
                ActionMechanics.interrupt_action(world, entity_id, context, flow, message)
                return False

        # 2. ターゲットロストチェック
        target_data = gauge.part_targets.get(gauge.selected_part)
        if target_data:
            target_id, target_part_type = target_data
            if not TargetingMechanics.is_action_target_valid(world, target_id, target_part_type):
                message = LogBuilder.get_target_lost(actor_name)
                ActionMechanics.interrupt_action(world, entity_id, context, flow, message)
                return False
        
        return True

    @staticmethod
    def handle_target_loss(world, entity_id: int, context, flow):
        comps = world.try_get_entity(entity_id)
        if not comps: return
        actor_name = comps['medal'].nickname
        message = LogBuilder.get_target_lost(actor_name)
        ActionMechanics.interrupt_action(world, entity_id, context, flow, message)

    @staticmethod
    def interrupt_action(world, entity_id: int, context, flow, message: str):
        context.battle_log.append(message)
        transition_to_phase(flow, BattlePhase.LOG_WAIT)
        
        comps = world.try_get_entity(entity_id)
        if not comps or 'gauge' not in comps: return

        gauge = comps['gauge']
        current_p = gauge.progress
        gauge.status = GaugeStatus.COOLDOWN
        gauge.progress = max(0.0, 100.0 - current_p)
        gauge.selected_action = None
        gauge.selected_part = None
        
        if entity_id in context.waiting_queue:
            context.waiting_queue.remove(entity_id)