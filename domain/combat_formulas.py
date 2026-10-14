"""戦闘における確率・ダメージ等の純粋な計算式（数理モデル）。"""
from typing import Dict
from domain.constants import PartType


def calculate_hit_probability(success: int, mobility: int) -> float:
    """命中率の計算式"""
    denominator = success + (mobility * 0.2)
    if denominator <= 0:
        return 1.0
    return max(0.05, min(0.95, success / denominator))


def calculate_break_probability(success: int, defense: int) -> float:
    """防御突破率の計算式"""
    denom = success + (defense * 2.0)
    if denom <= 0:
        return 1.0
    return max(0.05, min(0.95, success / denom))


def calculate_damage(
    attack: int,
    success: int,
    target_mobility: int,
    target_defense: int,
    is_guarded: bool,
    is_critical: bool,
) -> int:
    """ダメージ値の計算式"""
    p_mobility = 0.0 if is_critical else target_mobility
    p_defense = target_defense if (is_guarded and not is_critical) else 0.0

    performance_diff = success - (p_mobility / 2.0) - (p_defense / 2.0)
    bonus_damage = max(0.0, performance_diff) / 2.0
    return int(attack + bonus_damage)


def get_best_guard_part(target_parts_hp: Dict[PartType, int]) -> PartType:
    """ガード・身代わり時の被弾部位（頭部以外の最大HP部位、すべて破壊済なら頭部）"""
    non_head_parts = {
        pt: hp for pt, hp in target_parts_hp.items()
        if pt != PartType.HEAD and hp > 0
    }
    if non_head_parts:
        return max(non_head_parts, key=non_head_parts.get)
    return PartType.HEAD
