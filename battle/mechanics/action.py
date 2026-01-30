"""アクションの状態遷移・妥当性検証ロジック"""

from typing import Tuple, Optional, List
from dataclasses import dataclass
from domain.constants import GaugeStatus, ActionType
from battle.mechanics.targeting import TargetingMechanics
from battle.mechanics.log import LogBuilder
from battle.mechanics.trait import TraitRegistry

@dataclass(frozen=True)
class GaugeResetData:
    """ゲージをリセットする際の計算済みパラメータ"""
    status: str
    progress: float
    clear_selection: bool = True

class ActionMechanics:
    """
    アクションに関する判断ロジックと状態更新ヘルパー。
    副作用（コンポーネント書き換え）は持たず、Systemに適用すべき値を計算して返す。
    """

    @staticmethod
    def get_cooldown_reset_data(current_progress: float, penalty_ratio: float = 1.0) -> GaugeResetData:
        """
        放熱状態へリセットするためのデータを計算する。
        """
        # 充填中断位置から放熱を開始するため、ゲージを反転させる
        if penalty_ratio > 0:
            new_progress = max(0.0, 100.0 - current_progress)
        else:
            new_progress = 0.0

        return GaugeResetData(
            status=GaugeStatus.COOLDOWN,
            progress=new_progress,
            clear_selection=True
        )

    @staticmethod
    def get_choice_reset_data() -> GaugeResetData:
        """
        行動選択状態へリセットするためのデータを計算する。
        """
        return GaugeResetData(
            status=GaugeStatus.ACTION_CHOICE,
            progress=0.0,
            clear_selection=True
        )

    @staticmethod
    def validate_action_continuity(world, entity_id: int) -> Tuple[bool, Optional[str]]:
        """
        アクションの継続妥当性を検証する（充填中のパーツ破壊チェックなど）。
        
        Returns:
            (is_valid, interruption_message)
        """
        comps = world.try_get_entity(entity_id)
        if not comps or 'gauge' not in comps:
            return True, None

        gauge = comps['gauge']
        if gauge.status != GaugeStatus.CHARGING:
            return True, None

        actor_name = comps['medal'].nickname
        
        # 1. 実行予定パーツの生存チェック
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            if not TargetingMechanics.is_action_target_valid(world, entity_id, gauge.selected_part):
                return False, LogBuilder.get_part_broken_interruption(actor_name)

        # 2. ターゲットの生存チェック
        target_data = gauge.part_targets.get(gauge.selected_part)
        if target_data:
            target_id, target_part_type = target_data
            if not TargetingMechanics.is_action_target_valid(world, target_id, target_part_type):
                return False, LogBuilder.get_target_lost(actor_name)
        
        return True, None

    @staticmethod
    def resolve_action_target(world, actor_eid: int, actor_comps, gauge) -> Tuple[Optional[int], Optional[str]]:
        """
        行動実行の瞬間に、特性やスキルの性質に基づいて最終的なターゲット（eid, part）を確定させる。
        """
        if gauge.selected_action != ActionType.ATTACK or not gauge.selected_part:
            return None, None

        # 実行パーツ自体の生存確認
        if not TargetingMechanics.is_part_alive(world, actor_eid, gauge.selected_part):
            return None, None

        part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
        p_comps = world.try_get_entity(part_id)
        attack_comp = p_comps.get('attack') if p_comps else None
        if not attack_comp:
            return None, None

        # 特性振る舞い（格闘/射撃のターゲット解決ロジック）に委譲
        trait_behavior = TraitRegistry.get(attack_comp.trait)
        return trait_behavior.resolve_target(world, actor_eid, actor_comps, gauge)