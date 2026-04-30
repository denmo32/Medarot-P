"""パーツ特性（Trait）の振る舞いロジック"""

from abc import ABC, abstractmethod
from typing import List
from domain.constants import TraitType
from domain.models import StatusEffect

class TraitBehavior(ABC):
    """特性の振る舞いを定義する基底クラス"""

    @abstractmethod
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        """攻撃命中時の追加効果リストを生成して返す。"""
        return []

class NormalTrait(TraitBehavior):
    """特別な効果を持たない標準的な特性"""
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        return []

class ThunderTrait(TraitBehavior):
    """サンダー：命中時に相手を停止させる。"""
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        # 成功度と機動の差分に応じて停止時間が決まる
        duration = max(0.5, (success - mobility) * 0.05)
        return [StatusEffect(type_id="stop", duration=duration)]

class SwordTrait(TraitBehavior):
    """ソード"""
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        return []

class HammerTrait(TraitBehavior):
    """ハンマー"""
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        return []


_behaviors = {
    TraitType.RIFLE: NormalTrait(),
    TraitType.GATLING: NormalTrait(),
    TraitType.SWORD: SwordTrait(),
    TraitType.HAMMER: HammerTrait(),
    TraitType.THUNDER: ThunderTrait(),
}

_default = NormalTrait()

def get_trait_behavior(trait_name: str) -> TraitBehavior:
    """指定された特性名の振る舞いを取得する。"""
    return _behaviors.get(trait_name, _default)
