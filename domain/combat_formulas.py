# domain/combat_formulas.py
"""戦闘における確率・ダメージ等の純粋な計算式（数理モデル）および部位選定ロジック。"""
from typing import Dict, Optional, Sequence
from domain.constants import PartType

# 非頭部パーツの既定選定順位（同HP時は 脚部 > 左腕 > 右腕）
DEFAULT_NON_HEAD_PRIORITY: Sequence[PartType] = (
    PartType.LEGS,
    PartType.LEFT_ARM,
    PartType.RIGHT_ARM,
)


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


def select_best_alive_part(
    parts_hp: Dict[PartType, int],
    priority_order: Sequence[PartType] = DEFAULT_NON_HEAD_PRIORITY,
    exclude: Optional[PartType] = None,
    allow_head_fallback: bool = True,
) -> Optional[PartType]:
    """生存している部位の中から、指定の優先順序・最大HP基準で最適な部位を選定する。"""
    best_part: Optional[PartType] = None
    best_hp = -1

    for pt in priority_order:
        if pt == exclude:
            continue
        hp = parts_hp.get(pt, 0)
        if hp > best_hp and hp > 0:
            best_part = pt
            best_hp = hp

    if best_part is not None:
        return best_part

    if allow_head_fallback and exclude != PartType.HEAD and parts_hp.get(PartType.HEAD, 0) > 0:
        return PartType.HEAD

    return None


def get_best_guard_part(target_parts_hp: Dict[PartType, int]) -> PartType:
    """ガード・身代わり時の被弾部位（頭部以外の最大HP部位、すべて破壊済なら頭部）"""
    return select_best_alive_part(target_parts_hp, allow_head_fallback=True) or PartType.HEAD


def select_pierce_target(
    target_parts_hp: Dict[PartType, int],
    excluded_part: PartType,
) -> Optional[PartType]:
    """貫通対象となる部位を選定する（被弾部位を除き、最大HPの非頭部部位、なければ頭部）。"""
    return select_best_alive_part(target_parts_hp, exclude=excluded_part, allow_head_fallback=True)