"""戦闘計算の純粋関数群。状態を持たず、入力から結果を導出する。"""

import logging
import random
from typing import Callable, Dict, List, Optional
from domain.constants import HitPolicy, PartType, PART_TYPE_LABELS
from domain.effect_payloads import AppliedEffect, PartDamage, PierceDamage
from domain.models import BattleParticipant, ActionResult
from domain.action_logic import get_action_definition
from domain.combat_formulas import (
    calculate_hit_probability,
    calculate_break_probability,
    calculate_damage,
    get_best_guard_part,
)

logger = logging.getLogger(__name__)

# 非頭部パーツの優先順位（同値時は脚部 > 左腕 > 右腕）
_NON_HEAD_PIERCE_PRIORITY = (
    PartType.LEGS,
    PartType.LEFT_ARM,
    PartType.RIGHT_ARM,
)


def _select_pierce_target(
    target_parts_hp: Dict[PartType, int],
    excluded_part: PartType,
) -> Optional[PartType]:
    """貫通対象となる部位を選定する。"""
    best_part: Optional[PartType] = None
    best_hp = -1

    for part_type in _NON_HEAD_PIERCE_PRIORITY:
        if part_type == excluded_part:
            continue

        hp = target_parts_hp.get(part_type, 0)
        if hp <= 0:
            continue

        if hp > best_hp:
            best_part = part_type
            best_hp = hp

    if best_part is not None:
        return best_part

    if excluded_part != PartType.HEAD and target_parts_hp.get(PartType.HEAD, 0) > 0:
        return PartType.HEAD

    return None


def determine_hit_part(
    target_parts_hp: Dict[PartType, int],
    target_part_type: PartType,
    is_guarded: bool,
) -> PartType:
    """被弾部位の決定（ガードロジックを含む）"""
    hit_part = target_part_type

    if is_guarded:
        hit_part = get_best_guard_part(target_parts_hp)

    if target_parts_hp.get(hit_part, 0) <= 0:
        label = PART_TYPE_LABELS.get(hit_part, hit_part.value)
        logger.error(f"【システムエラー】被弾予定部位「{label}」が破壊済みです。")
        hit_part = PartType.HEAD

    return hit_part


def resolve_attack(
    attacker: BattleParticipant,
    target: BattleParticipant,
    target_part_type: PartType,
    rng: Optional[Callable[[], float]] = None,
) -> ActionResult:
    """攻撃解決の統合ロジック。命中率・防御突破・部位決定・ダメージ・貫通を純粋に算出する。"""
    _random = rng or random.random

    # 1. 行動形式の実装取得
    action_def = get_action_definition(attacker.stats.action)
    atk_mobility = attacker.legs_stats.get("mobility", 0)
    atk_defense = attacker.legs_stats.get("defense", 0)
    action_bonuses = action_def.offensive_bonus_fn(atk_mobility, atk_defense)

    # 2. 防御側のペナルティ評価
    prevent_guard, force_hit, force_critical = False, False, False
    target_action_def = target.defensive_info.action_def
    if target_action_def:
        prevent_guard, force_hit, force_critical = target_action_def.defensive_penalty_fn(
            target.defensive_info.gauge_status
        )

    # 3. 最終補正済みステータス
    adjusted_success = max(
        1,
        attacker.stats.success + action_bonuses.success + attacker.buff_success,
    )
    adjusted_attack = max(1, attacker.stats.attack + action_bonuses.attack)
    adjusted_mobility = max(0, target.legs_stats.get("mobility", 0))
    adjusted_defense = max(0, target.legs_stats.get("defense", 0))

    # 4. 命中判定
    hit_prob = calculate_hit_probability(adjusted_success, adjusted_mobility)
    never_miss = attacker.stats.hit_policy == HitPolicy.NEVER_MISS
    is_hit = force_hit or never_miss or (_random() < hit_prob)
    if not is_hit:
        return ActionResult(
            success=False,
            adjusted_success=adjusted_success,
            adjusted_mobility=adjusted_mobility,
            skill=attacker.stats.skill,
        )

    # 5. 防御突破・クリティカル判定
    is_critical = False
    if force_critical:
        is_guarded = False
        is_critical = True
    else:
        break_prob = calculate_break_probability(adjusted_success, adjusted_defense)
        is_break_success = _random() < break_prob
        is_guarded = not is_break_success

        if is_break_success and (hit_prob + break_prob) >= 1.7:
            is_critical = True

        if prevent_guard:
            is_guarded = False

    # 6. 被弾部位の決定
    hit_part = determine_hit_part(target.parts_hp, target_part_type, is_guarded)

    # 7. ダメージ計算
    damage = calculate_damage(
        adjusted_attack,
        adjusted_success,
        adjusted_mobility,
        adjusted_defense,
        is_guarded,
        is_critical,
    )

    if target.damage_reduction > 0:
        damage = max(1, damage - target.damage_reduction)

    target_hp_before = target.parts_hp.get(hit_part, 0)
    effective_damage = min(damage, target_hp_before)
    is_destroyed = damage >= target_hp_before

    # 8. 適用ペイロードの構築
    applied_effects: List[AppliedEffect] = [
        PartDamage(
            part_type=hit_part,
            amount=damage,
            effective_damage=effective_damage,
            destroyed=is_destroyed,
        )
    ]

    # 貫通判定
    if (
        attacker.stats.can_pierce
        and hit_part != PartType.HEAD
        and is_destroyed
    ):
        overflow = damage - target_hp_before
        if overflow > 0:
            pierce_part = _select_pierce_target(target.parts_hp, hit_part)
            if pierce_part is not None:
                pierce_target_hp = target.parts_hp.get(pierce_part, 0)
                pierce_effective = min(overflow, pierce_target_hp)
                applied_effects.append(
                    PierceDamage(
                        part_type=pierce_part,
                        amount=overflow,
                        effective_damage=pierce_effective,
                        destroyed=overflow >= pierce_target_hp,
                    )
                )

    return ActionResult(
        success=True,
        is_guarded=is_guarded,
        is_critical=is_critical,
        skill=attacker.stats.skill,
        applied_effects=tuple(applied_effects),
        adjusted_success=adjusted_success,
        adjusted_mobility=adjusted_mobility,
    )