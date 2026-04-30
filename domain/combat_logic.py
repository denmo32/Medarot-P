"""戦闘計算ロジック（純粋関数群）"""

import random
from typing import Optional, Tuple, Dict, List
from domain.constants import PartType, GaugeStatus
from domain.models import (
    CombatStats, DefensivePenalty, AttackParams, MedalParams, LegsStats, 
    CombatResult, AttackQuality, StatusEffect
)
from domain.attribute import calculate_affinity_bonus
from domain.skill_logic import get_skill_behavior
from domain.trait_logic import get_trait_behavior

# --- 基礎計算式 (from combat_formula.py) ---

MOBILITY_WEIGHT = 0.2       # 回避率計算時の機動性の重み
DEFENSE_WEIGHT = 2.0        # 突破率計算時の防御力の重み
CRITICAL_THRESHOLD = 2.0    # クリティカル発生閾値
DAMAGE_PENALTY_DIVISOR = 2.0 # ダメージボーナス計算時の除数
MIN_PROBABILITY = 0.05      # 最小確率
MAX_PROBABILITY = 0.95      # 最大確率

def calculate_hit_probability_base(success: int, mobility: int) -> float:
    """命中率の基礎計算"""
    denominator = success + (mobility * MOBILITY_WEIGHT)
    if denominator <= 0:
        return 1.0
    return max(MIN_PROBABILITY, min(MAX_PROBABILITY, success / denominator))

def calculate_break_probability(success: int, defense: int) -> float:
    """防御突破率の基礎計算"""
    denominator = success + (defense * DEFENSE_WEIGHT)
    if denominator <= 0:
        return 1.0
    return max(MIN_PROBABILITY, min(MAX_PROBABILITY, success / denominator))

def check_is_hit(hit_prob: float, rng: Optional[random.Random] = None) -> bool:
    """命中判定"""
    source = rng if rng else random
    return source.random() < hit_prob

def check_attack_outcome(hit_prob: float, break_prob: float, rng: Optional[random.Random] = None) -> Tuple[bool, bool]:
    """攻撃の結果詳細（クリティカル、防御成功）を判定"""
    source = rng if rng else random
    is_break_success = (source.random() < break_prob)
    is_defense = not is_break_success
    is_critical = False
    if is_break_success:
        if (hit_prob + break_prob) >= CRITICAL_THRESHOLD:
            is_critical = True
    return is_critical, is_defense

def calculate_damage_value(base_attack: int, success: int, mobility: int, defense: float, 
                         is_critical: bool, is_defense: bool) -> int:
    """ダメージ値の基礎計算"""
    if is_critical:
        penalty_mobility = 0.0
        penalty_defense = 0.0
    elif not is_defense:
        penalty_mobility = float(mobility)
        penalty_defense = 0.0
    else:
        penalty_mobility = float(mobility)
        penalty_defense = float(defense)
    
    performance_diff = success - (penalty_mobility / DAMAGE_PENALTY_DIVISOR) - (penalty_defense / DAMAGE_PENALTY_DIVISOR)
    bonus_damage = max(0.0, performance_diff) / 2.0
    return int(base_attack + bonus_damage)

# --- 統合された計算ロジック (from HitCalculator / DamageCalculator) ---

def calculate_adjusted_stats(
    attacker_medal: MedalParams,
    attacker_part: AttackParams,
    attacker_legs: LegsStats,
    target_medal: MedalParams,
    target_legs: LegsStats
) -> CombatStats:
    """ステータス補正を一括計算する"""
    atk_bonus, def_bonus = calculate_affinity_bonus(
        attacker_medal.attribute,
        attacker_part.part_attribute,
        target_medal.attribute
    )

    skill_behavior = get_skill_behavior(attacker_part.skill_type)
    s_success_bonus, s_attack_bonus = skill_behavior.get_offensive_bonuses(
        attacker_legs.mobility,
        attacker_legs.defense
    )

    return CombatStats(
        success=max(1, attacker_part.success + atk_bonus + s_success_bonus),
        attack=max(1, attacker_part.attack + atk_bonus + s_attack_bonus),
        tgt_mobility=max(0, target_legs.mobility + def_bonus),
        tgt_defense=max(0, target_legs.defense + def_bonus)
    )

def get_defensive_penalty(
    target_gauge_status: str,
    target_selected_part: Optional[str],
    target_part_skill_type: Optional[str]
) -> DefensivePenalty:
    """ターゲット側の防御制限を取得する"""
    if not target_gauge_status or not target_selected_part or not target_part_skill_type:
        return DefensivePenalty()

    skill_behavior = get_skill_behavior(target_part_skill_type)
    prevent_defense, force_hit, force_critical = skill_behavior.get_defensive_penalty(target_gauge_status)

    return DefensivePenalty(
        prevent_defense=prevent_defense,
        force_hit=force_hit,
        force_critical=force_critical
    )

def evaluate_attack_quality(
    success: int,
    tgt_defense: int,
    hit_prob: float,
    prevent_defense: bool,
    force_critical: bool = False,
    rng: Optional[random.Random] = None
) -> AttackQuality:
    """クリティカルか、防御成功かを判定する"""
    if force_critical:
        return AttackQuality(is_critical=True, is_defense=False)

    break_prob = calculate_break_probability(success, tgt_defense)
    is_critical, is_defense = check_attack_outcome(hit_prob, break_prob, rng)

    if prevent_defense:
        is_defense = False

    return AttackQuality(is_critical=is_critical, is_defense=is_defense)

def calculate_combat_result(
    stats: CombatStats,
    penalty: DefensivePenalty,
    trait_name: str,
    target_part_hps: Dict[str, int],
    target_desired_part: Optional[str],
    rng: Optional[random.Random] = None
) -> CombatResult:
    """一連の戦闘計算を実行して結果を返す"""
    # 1. 命中判定
    if penalty.force_hit:
        hit_prob, is_hit = 1.0, True
    else:
        hit_prob = calculate_hit_probability_base(stats.success, stats.tgt_mobility)
        is_hit = check_is_hit(hit_prob, rng)

    if not is_hit:
        return CombatResult.miss()

    # 2. 攻撃性質の決定
    quality = evaluate_attack_quality(
        stats.success, stats.tgt_defense, hit_prob, 
        penalty.prevent_defense, penalty.force_critical, rng
    )

    # 3. 被弾部位の決定 (Targeting logic - simplified call)
    from domain.targeting_logic import resolve_hit_part
    hit_part = resolve_hit_part(target_part_hps, target_desired_part, quality.is_defense, rng)

    # 4. ダメージ計算
    damage = calculate_damage_value(
        stats.attack, stats.success, stats.tgt_mobility, stats.tgt_defense,
        quality.is_critical, quality.is_defense
    )

    # 5. 特性による追加効果
    trait_behavior = get_trait_behavior(trait_name)
    added_effects = trait_behavior.get_added_effects(stats.success, stats.tgt_mobility)

    return CombatResult(
        is_hit=True,
        is_critical=quality.is_critical,
        is_defense=quality.is_defense,
        damage=damage,
        hit_part=hit_part,
        added_effects=added_effects
    )
