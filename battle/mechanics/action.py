"""アクションの状態遷移・妥当性検証ロジック"""

from typing import Tuple, Optional
from domain.constants import GaugeStatus, ActionType
from battle.mechanics.targeting import TargetingMechanics
from battle.mechanics.log import LogBuilder
from battle.mechanics.trait import TraitRegistry

class ActionMechanics:
    """
    アクションに関する判断ロジックと状態更新ヘルパー。
    副作用（ログ追加、フェーズ遷移など）は持たず、Systemに委譲する。
    """

    @staticmethod
    def reset_to_cooldown(gauge):
        """ゲージを放熱状態にリセットするデータ操作ヘルパー"""
        gauge.status = GaugeStatus.COOLDOWN
        gauge.progress = 0.0
        gauge.selected_action = None
        gauge.selected_part = None

    @staticmethod
    def validate_action_continuity(world, entity_id: int) -> Tuple[bool, Optional[str]]:
        """
        アクションの継続妥当性を検証する。
        
        Returns:
            (is_valid, interruption_message)
            - is_valid: 継続可能ならTrue
            - interruption_message: 中断が必要な場合のログメッセージ
        """
        comps = world.try_get_entity(entity_id)
        if not comps or 'gauge' not in comps:
            return True, None

        gauge = comps['gauge']
        # 充填中以外は検証不要
        if gauge.status != GaugeStatus.CHARGING:
            return True, None

        actor_name = comps['medal'].nickname
        
        # 1. パーツ破壊チェック（使用しようとしているパーツが壊れていないか）
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            if not TargetingMechanics.is_action_target_valid(world, entity_id, gauge.selected_part):
                return False, LogBuilder.get_part_broken_interruption(actor_name)

        # 2. ターゲットロストチェック（狙っていた相手が存在するか）
        target_data = gauge.part_targets.get(gauge.selected_part)
        if target_data:
            target_id, target_part_type = target_data
            if not TargetingMechanics.is_action_target_valid(world, target_id, target_part_type):
                return False, LogBuilder.get_target_lost(actor_name)
        
        return True, None

    @staticmethod
    def resolve_action_target(world, actor_eid: int, actor_comps, gauge) -> Tuple[Optional[int], Optional[str]]:
        """
        行動実行の瞬間に最終的なターゲットを確定させる。
        TargetingMechanics（生存確認）と TraitRegistry（特性による動的変更）を統合して判断する。
        """
        if gauge.selected_action != ActionType.ATTACK or not gauge.selected_part:
            return None, None

        # 実行パーツの有効性確認
        if not TargetingMechanics.is_part_alive(world, actor_eid, gauge.selected_part):
            return None, None

        part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
        p_comps = world.try_get_entity(part_id)
        attack_comp = p_comps.get('attack') if p_comps else None
        if not attack_comp:
            return None, None

        # 特性振る舞いに解決を委譲
        trait_behavior = TraitRegistry.get(attack_comp.trait)
        return trait_behavior.resolve_target(world, actor_eid, actor_comps, gauge)