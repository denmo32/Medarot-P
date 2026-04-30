"""属性関連ロジック"""

from typing import Dict, Any, Tuple
from domain.constants import PartType, AttributeType

def get_single_affinity_score(atk_attr: str, def_attr: str) -> int:
    """単体の属性相性スコアを計算 (Power > Technique > Speed > Power)"""
    if atk_attr == AttributeType.UNDEFINED or def_attr == AttributeType.UNDEFINED:
        return 0
    if atk_attr == def_attr:
        return 0

    if atk_attr == AttributeType.POWER:
        return 1 if def_attr == AttributeType.TECHNIQUE else -1
    if atk_attr == AttributeType.TECHNIQUE:
        return 1 if def_attr == AttributeType.SPEED else -1
    if atk_attr == AttributeType.SPEED:
        return 1 if def_attr == AttributeType.POWER else -1
    return 0

def calculate_affinity_bonus(atk_medal_attr: str, atk_part_attr: str, def_medal_attr: str) -> Tuple[int, int]:
    """
    3すくみに基づく属性相性ボーナスを計算する。

    Returns:
        (atk_bonus, def_bonus)
        - atk_bonus: 攻撃側の success, attack に加算
        - def_bonus: 防御側の mobility, defense に加算（攻撃側有利ならマイナス）
    """
    score1 = get_single_affinity_score(atk_medal_attr, def_medal_attr)
    score2 = get_single_affinity_score(atk_part_attr, def_medal_attr)

    # スコア合計: +2, +1, 0, -1, -2
    total_score = score1 + score2

    # 係数: 5
    factor = 5

    atk_mod = total_score * factor
    def_mod = total_score * factor * -1 

    return atk_mod, def_mod

def apply_passive_stats_bonus(original_stats: Dict[str, Any], part_type: str, medal_attr: str) -> Dict[str, Any]:
    """
    メダル属性とパーツ属性の一致によるパッシブボーナスを適用した新しいstats辞書を返す。
    EntityFactoryで使用される。
    """
    stats = original_stats.copy()
    part_attr = stats.get("attribute", AttributeType.UNDEFINED)

    # 属性不一致ならそのまま返す
    if medal_attr != part_attr or medal_attr == AttributeType.UNDEFINED:
        return stats

    if medal_attr == AttributeType.SPEED:
        # スピード: 脚部の機動+20, 攻撃パーツの時間短縮(x0.8)
        if part_type == PartType.LEGS:
            stats["mobility"] = stats.get("mobility", 0) + 20
        else:
            stats["time_modifier"] = 0.8

    elif medal_attr == AttributeType.POWER:
        # パワー: 全パーツHP+5, 脚部以外の攻撃+10
        stats["hp"] = stats.get("hp", 0) + 5
        if part_type != PartType.LEGS and stats["attack"] is not None:
            stats["attack"] += 10
            # base_attack は加算しない（時間計算への影響を避けるため）

    elif medal_attr == AttributeType.TECHNIQUE:
        # テクニック: 脚部以外の成功+20, 脚部の防御+10
        if part_type == PartType.LEGS:
            stats["defense"] = stats.get("defense", 0) + 10
        else:
            stats["success"] = stats.get("success", 0) + 20

    return stats