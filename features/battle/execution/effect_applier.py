"""適用オブジェクトを行動結果からバトルの世界状態へ反映するハンドラ。"""
import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Dict, Optional, Type

from domain.effect_payloads import (
    AppliedEffect,
    ApplyStatus,
    DamageEffect,
    PartDamage,
    PartRepair,
    PartRestore,
    PierceDamage,
    TrapInstall,
)
from ..entities.commands import ExecutionReport

if TYPE_CHECKING:
    from ..context import BattleContext
    from ..entities.robot import Robot


@dataclass
class ApplyContext:
    actor: 'Robot'
    target: Optional['Robot'] = None
    battle: Optional['BattleContext'] = None


EffectHandler = Callable[[AppliedEffect, ApplyContext], Optional[AppliedEffect]]


def _apply_damage_effect(effect: DamageEffect, ctx: ApplyContext) -> Optional[AppliedEffect]:
    if ctx.target is None:
        return None
    actual_dmg, destroyed = ctx.target.apply_damage(effect.part_type, effect.amount)
    return dataclasses.replace(effect, effective_damage=actual_dmg, destroyed=destroyed)


def _apply_part_repair(effect: PartRepair, ctx: ApplyContext) -> Optional[AppliedEffect]:
    if ctx.target is None:
        return None
    res = ctx.target.apply_repair(effect.amount, effect.part_type)
    if res is None:
        return None
    _, actual = res
    return dataclasses.replace(effect, amount=actual)


def _apply_part_restore(effect: PartRestore, ctx: ApplyContext) -> Optional[AppliedEffect]:
    if ctx.target is None:
        return None
    restored_part = ctx.target.apply_restore(effect.part_type)
    if restored_part is None:
        return None
    return dataclasses.replace(effect, part_type=restored_part)


def _apply_trap_install(effect: TrapInstall, ctx: ApplyContext) -> Optional[AppliedEffect]:
    if ctx.battle is None or ctx.target is None:
        return None
    installed_trap = dataclasses.replace(
        effect.trap, target_team=ctx.target.team, source_name=ctx.actor.name
    )
    ctx.battle.traps.install(installed_trap)
    return dataclasses.replace(effect, trap=installed_trap)


def _apply_status_effect(effect: ApplyStatus, ctx: ApplyContext) -> Optional[AppliedEffect]:
    recipient = ctx.actor if effect.target_self else ctx.target
    if recipient is None:
        return None
    recipient.apply_status(effect.effect)
    return effect


EFFECT_HANDLERS: Dict[Type[AppliedEffect], EffectHandler] = {
    PartDamage: _apply_damage_effect,
    PierceDamage: _apply_damage_effect,
    PartRepair: _apply_part_repair,
    PartRestore: _apply_part_restore,
    TrapInstall: _apply_trap_install,
    ApplyStatus: _apply_status_effect,
}


def apply_action_effects(
    report: ExecutionReport, actor: 'Robot', ctx: Optional['BattleContext'] = None
) -> ExecutionReport:
    """適用オブジェクトを世界状態へ反映する（副作用はハンドラ経由のみ）。"""
    result = report.result
    target = report.target

    if result is None or not result.success or target is None or not result.applied_effects:
        return report

    apply_ctx = ApplyContext(actor=actor, target=target, battle=ctx)
    applied = []
    for eff in result.applied_effects:
        handler = EFFECT_HANDLERS.get(type(eff))
        if handler:
            res = handler(eff, apply_ctx)
            if res is not None:
                applied.append(res)
        else:
            applied.append(eff)

    if tuple(applied) != result.applied_effects:
        updated_result = dataclasses.replace(result, applied_effects=tuple(applied))
        return dataclasses.replace(report, result=updated_result)

    return report