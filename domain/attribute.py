"""属性関連ロジック（パッシブボーナスのみ管理）"""

from dataclasses import dataclass
from domain.constants import PartType, AttributeType


@dataclass(frozen=True)
class PassiveBonuses:
    """属性一致によるパッシブボーナスの計算結果"""
    hp_add: int = 0
    attack_add: int = 0
    success_add: int = 0
    mobility_add: int = 0
    defense_add: int = 0
    time_modifier: float = 1.0


def get_passive_bonuses(part_type: PartType, part_attr: AttributeType, medal_attr: AttributeType) -> PassiveBonuses:
    """メダル属性とパーツ属性の一致によるパッシブボーナスを計算する"""
    if medal_attr != part_attr or medal_attr == AttributeType.UNDEFINED:
        return PassiveBonuses()

    is_legs = (part_type == PartType.LEGS)

    if medal_attr == AttributeType.SPEED:
        return PassiveBonuses(mobility_add=20) if is_legs else PassiveBonuses(time_modifier=0.8)

    if medal_attr == AttributeType.POWER:
        return PassiveBonuses(hp_add=5, attack_add=0 if is_legs else 10)

    if medal_attr == AttributeType.TECHNIQUE:
        return PassiveBonuses(defense_add=10) if is_legs else PassiveBonuses(success_add=20)

    return PassiveBonuses()
