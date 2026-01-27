"""パーツ特性（Trait）に関連するロジック（Strategyパターン）"""

from abc import ABC, abstractmethod
from typing import Tuple
from battle.constants import TraitType

class TraitBehavior(ABC):
    """特性の振る舞いを定義する基底クラス"""

    @abstractmethod
    def get_stop_duration(self, success: int, mobility: int) -> float:
        """
        攻撃命中時の停止時間（秒）を計算する。
        追加効果がない場合は0.0を返す。
        """
        return 0.0

class NormalTrait(TraitBehavior):
    """特別な効果を持たない標準的な特性（ライフル、ソードなど）"""
    def get_stop_duration(self, success: int, mobility: int) -> float:
        return 0.0

class ThunderTrait(TraitBehavior):
    """サンダー：命中時に相手を停止させる"""
    def get_stop_duration(self, success: int, mobility: int) -> float:
        # 成功度と機動の差分に応じて停止時間が決まる
        return max(0.5, (success - mobility) * 0.05)


class TraitRegistry:
    """TraitBehaviorのカタログ（Registry）"""
    
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
        """IDに応じた特性振る舞いを返す"""
        return cls._behaviors.get(trait_name, cls._default)