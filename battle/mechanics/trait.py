"""パーツ特性（Trait）の振る舞いロジック"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from domain.constants import TraitType
from components.battle_component import StatusEffect
from battle.mechanics.targeting import TargetingMechanics

class TraitBehavior(ABC):
    """特性の振る舞いを定義する基底クラス"""

    @abstractmethod
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        """攻撃命中時の追加効果リストを生成して返す。"""
        return []

    def resolve_target(self, world, actor_eid: int, actor_comps, gauge) -> Tuple[Optional[int], Optional[str]]:
        """
        行動実行時に最終的なターゲットを確定させる。
        デフォルト（射撃等）は予約されたターゲットをそのまま使用する。
        """
        target_data = gauge.part_targets.get(gauge.selected_part)
        if target_data:
            tid, tpart = target_data
            if TargetingMechanics.is_action_target_valid(world, tid, tpart):
                return tid, tpart
        return None, None

class MeleeTrait(TraitBehavior):
    """格闘特性の基底：ターゲットを中央に近い敵へ動的に変更する。"""
    def resolve_target(self, world, actor_eid: int, actor_comps, gauge) -> Tuple[Optional[int], Optional[str]]:
        target_id = TargetingMechanics.get_closest_target_by_gauge(world, actor_comps['team'].team_type)
        target_part = TargetingMechanics.get_random_alive_part(world, target_id) if target_id else None
        return target_id, target_part

class NormalTrait(TraitBehavior):
    """特別な効果を持たない標準的な特性"""
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        return []

class ThunderTrait(MeleeTrait):
    """サンダー：命中時に相手を停止させる。"""
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        # 成功度と機動の差分に応じて停止時間が決まる
        duration = max(0.5, (success - mobility) * 0.05)
        return [StatusEffect(type_id="stop", duration=duration)]

class SwordTrait(MeleeTrait):
    """ソード"""
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        return []

class HammerTrait(MeleeTrait):
    """ハンマー"""
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        return []

class TraitRegistry:
    """TraitBehaviorのカタログ"""
    
    _behaviors = {
        TraitType.RIFLE: NormalTrait(),
        TraitType.GATLING: NormalTrait(),
        TraitType.SWORD: SwordTrait(),
        TraitType.HAMMER: HammerTrait(),
        TraitType.THUNDER: ThunderTrait(),
    }
    
    _default = NormalTrait()

    @classmethod
    def get(cls, trait_name: str) -> TraitBehavior:
        return cls._behaviors.get(trait_name, cls._default)