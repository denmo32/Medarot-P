"""パーツ特性（Trait）の振る舞いロジック"""

from abc import ABC, abstractmethod
from typing import List
from domain.constants import TraitType
from components.battle_component import StatusEffect

class TraitBehavior(ABC):
    """特性の振る舞いを定義する基底クラス"""

    @abstractmethod
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        """
        攻撃命中時の追加効果リストを生成して返す。
        """
        return []

class NormalTrait(TraitBehavior):
    """特別な効果を持たない標準的な特性"""
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        return []

class ThunderTrait(TraitBehavior):
    """サンダー：命中時に相手を停止させる"""
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        # 成功度と機動の差分に応じて停止時間が決まる
        duration = max(0.5, (success - mobility) * 0.05)
        return [StatusEffect(type_id="stop", duration=duration)]


class TraitRegistry:
    """TraitBehaviorのカタログ"""
    
    _behaviors = {
        TraitType.RIFLE: NormalTrait(),
        TraitType.GATLING: NormalTrait(),
        TraitType.SWORD: NormalTrait(),
        TraitType.HAMMER: NormalTrait(),
        TraitType.THUNDER: ThunderTrait(),
    }
    
    _default = NormalTrait()

    @classmethod
    def get(cls, trait_name: str) -> TraitBehavior:
        return cls._behaviors.get(trait_name, cls._default)