"""戦闘・行動効果の計算と生成（RNG 一元化）"""
from typing import Optional
from domain.constants import EffectType, PartType, EffectStackPolicy, SkillType, TeamType
from domain.models import StatusEffect, ActionResult, EffectResolutionContext, RepairResult
from domain.combat_formulas import calculate_hit_probability
from domain.traps import InstalledTrap


def calculate_stop_duration(attack: int, adjusted_success: int, adjusted_mobility: int) -> float:
    base_duration = max(0.5, (attack or 0) * 0.1)
    modifier = max(0.5, min(2.0, 1.0 + (adjusted_success - adjusted_mobility) * 0.02))
    return round(base_duration * modifier, 2)


def make_stop_effect(duration: float, part_type: Optional[PartType] = None) -> StatusEffect:
    return StatusEffect(type=EffectType.STOP, duration=duration, part_type=part_type)


def resolve_stop_effect(context: EffectResolutionContext) -> ActionResult:
    adj_success = max(1, context.attacker_success + context.proficiency_bonus)
    adj_mobility = max(0, context.target_mobility)
    target_part_type = context.target_part_type

    hit_prob = calculate_hit_probability(adj_success, adj_mobility)
    roll = context.rng.random()
    is_success = roll < hit_prob

    if is_success:
        duration = calculate_stop_duration(context.attacker_attack, adj_success, adj_mobility)
        effect = make_stop_effect(duration, part_type=target_part_type)
        return ActionResult(
            success=True,
            status_effect=effect,
            target_part=target_part_type,
            adjusted_success=adj_success,
            adjusted_mobility=adj_mobility,
            skill=context.skill,
        )
    return ActionResult(
        success=False,
        target_part=target_part_type,
        adjusted_success=adj_success,
        adjusted_mobility=adj_mobility,
        skill=context.skill,
    )


def resolve_repair_effect(context: EffectResolutionContext) -> ActionResult:
    max_hp_map = context.target_parts_max_hp
    healable = {
        pt: hp
        for pt, hp in context.target_parts_hp.items()
        if hp > 0 and hp < max_hp_map.get(pt, hp)
    }

    if not healable:
        return ActionResult(success=False, skill=context.skill)

    target_part = min(healable.items(), key=lambda x: x[1])[0]
    amount = max(1, context.attacker_attack)

    return ActionResult(
        success=True,
        repair_result=RepairResult(part_type=target_part, amount=amount),
        target_part=target_part,
        skill=context.skill,
    )


_RESTORE_PRIORITY = (PartType.LEGS, PartType.RIGHT_ARM, PartType.LEFT_ARM)


def resolve_restore_effect(context: EffectResolutionContext) -> ActionResult:
    broken_parts = [
        pt for pt, hp in context.target_parts_hp.items()
        if hp <= 0 and pt != PartType.HEAD
    ]

    if not broken_parts:
        return ActionResult(success=False, skill=context.skill)

    target_part = next((pt for pt in _RESTORE_PRIORITY if pt in broken_parts), broken_parts[0])

    return ActionResult(
        success=True,
        repair_result=RepairResult(part_type=target_part, is_restored=True),
        target_part=target_part,
        skill=context.skill,
    )


SCAN_SUCCESS_DIVISOR = 10


def resolve_scan_effect(context: EffectResolutionContext) -> ActionResult:
    raw_count = context.attacker_success // SCAN_SUCCESS_DIVISOR
    bonus_value = max(0, context.attacker_attack)

    if raw_count <= 0:
        return ActionResult(success=False, skill=context.skill)

    effect = StatusEffect(
        type=EffectType.SUCCESS_UP,
        duration=float("inf"),
        magnitude=bonus_value,
        charges=raw_count,
        source=context.skill.value if context.skill else None,
        stack_policy=EffectStackPolicy.CHARGES_MAX,
    )

    return ActionResult(
        success=True,
        status_effect=effect,
        skill=context.skill,
    )


def resolve_block_effect(context: EffectResolutionContext) -> ActionResult:
    effect = StatusEffect(
        type=EffectType.BLOCK,
        duration=float("inf"),
        source=context.skill.value if context.skill else None,
        stack_policy=EffectStackPolicy.REFRESH_MAX,
    )
    return ActionResult(
        success=True,
        status_effect=effect,
        status_to_self=True,
        skill=context.skill,
    )


def resolve_trap_effect(context: EffectResolutionContext) -> ActionResult:
    damage = max(1, context.attacker_attack)
    trap = InstalledTrap(
        skill=context.skill or SkillType.SHOOTING_TRAP,
        target_team=TeamType.ENEMY,
        source_name="",
        damage=damage,
    )
    return ActionResult(
        success=True,
        skill=context.skill,
        installed_trap=trap,
    )


def resolve_protect_effect(context: EffectResolutionContext) -> ActionResult:
    effect = StatusEffect(
        type=EffectType.PROTECT,
        duration=float("inf"),
        magnitude=max(1, context.attacker_attack),
        source=context.skill.value if context.skill else None,
        stack_policy=EffectStackPolicy.REFRESH_MAX,
        part_type=context.source_part_type,
    )
    return ActionResult(
        success=True,
        status_effect=effect,
        status_to_self=True,
        target_part=context.source_part_type,
        skill=context.skill,
    )