"""パーツ特性（Trait）の振る舞いロジック"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict
from domain.constants import TraitType
from components.battle_component import StatusEffect
from battle.mechanics.targeting import TargetingMechanics
from battle.mechanics.personality import PersonalityRegistry

class TraitBehavior(ABC):
    """特性の振る舞いを定義する基底クラス"""

    @abstractmethod
    def get_added_effects(self, success: int, mobility: int) -> List[StatusEffect]:
        """攻撃命中時の追加効果リストを生成して返す。"""
        return []

    def resolve_target(
        self,
        selected_part: Optional[str],
        part_targets: Dict[Optional[str], Tuple[int, Optional[str]]],
        is_target_alive: bool
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        行動実行時にターゲットを確定させる。
        デフォルト（射撃等）は予約されたターゲットを使用する。
        
        Args:
            selected_part: 選択中のパーツ種別
            part_targets: パーツごとのターゲット情報 {part_type: (target_id, target_part)}
            is_target_alive: ターゲットが生存しているか
        
        Returns:
            (target_id, target_part) のタプル。無効な場合は (None, None)
        """
        target_data = part_targets.get(selected_part)
        if target_data:
            tid, tpart = target_data
            if is_target_alive:
                return tid, tpart
        return None, None

class MeleeTrait(TraitBehavior):
    """
    格闘特性の基底：
    1. ターゲット機体は「中央に近い敵」に決定する。
    2. ターゲット部位は「攻撃者の性格」に基づいて決定する。
    """
    def resolve_target(
        self,
        closest_enemy_id: Optional[int],
        personality_id: str,
        target_part: Optional[str],
        is_target_alive: bool
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        格闘特性のターゲット解決。
        
        Args:
            closest_enemy_id: 最もゲージが進んでいる敵の ID
            personality_id: 性格 ID
            target_part: 性格によって選択された部位
            is_target_alive: ターゲットが生存しているか
        
        Returns:
            (target_id, target_part) のタプル。無効な場合は (None, None)
        """
        if not closest_enemy_id:
            return None, None
        
        if is_target_alive:
            return closest_enemy_id, target_part
        
        return None, None

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
    """TraitBehavior のカタログ"""

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
