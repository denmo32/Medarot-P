# features/battle/simulation/execution/effect_applier.py
"""適用オブジェクトを行動結果からバトルの世界状態（Robot/Trap）へ反映するハンドラ。"""
import dataclasses
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Type, TYPE_CHECKING

from domain.effect_payloads import (
    AppliedEffect,
    ApplyStatus,
    DamageEffect,
    PartRepair,
    PartRestore,
    TrapInstall,
)

if TYPE_CHECKING:
    from ..context import BattleContext
    from ..entities.commands import ExecutionReport
    from ..entities.robot import Robot


@dataclass(frozen=True)
class ApplyContext:
    actor: 'Robot'
    target: Optional['Robot'] = None
    battle: Optional['BattleContext'] = None


EffectApplierFn = Callable[[AppliedEffect, ApplyContext], Optional[AppliedEffect]]


# === 副作用適用ハンドラ群 ===

def _apply_damage(effect: AppliedEffect, ctx: ApplyContext) -> Optional[AppliedEffect]:
    if ctx.target is None or not isinstance(effect, DamageEffect):
        return None
    actual_dmg, destroyed = ctx.target.apply_damage(effect.part_type, effect.amount)
    return dataclasses.replace(effect, effective_damage=actual_dmg, destroyed=destroyed)


def _apply_part_repair(effect: AppliedEffect, ctx: ApplyContext) -> Optional[AppliedEffect]:
    if ctx.target is None or not isinstance(effect, PartRepair):
        return None
    res = ctx.target.apply_repair(effect.amount, effect.part_type)
    if res is None:
        return None
    _, actual = res
    return dataclasses.replace(effect, amount=actual)


def _apply_part_restore(effect: AppliedEffect, ctx: ApplyContext) -> Optional[AppliedEffect]:
    if ctx.target is None or not isinstance(effect, PartRestore):
        return None
    restored_part = ctx.target.apply_restore(effect.part_type)
    if restored_part is None:
        return None
    return dataclasses.replace(effect, part_type=restored_part)


def _apply_trap_install(effect: AppliedEffect, ctx: ApplyContext) -> Optional[AppliedEffect]:
    if ctx.battle is None or ctx.target is None or not isinstance(effect, TrapInstall):
        return None
    installed_trap = dataclasses.replace(
        effect.trap, target_team=ctx.target.team, source_name=ctx.actor.name
    )
    ctx.battle.traps.install(installed_trap)
    return dataclasses.replace(effect, trap=installed_trap)


def _apply_status_effect(effect: AppliedEffect, ctx: ApplyContext) -> Optional[AppliedEffect]:
    if not isinstance(effect, ApplyStatus):
        return None
    recipient = ctx.actor if effect.target_self else ctx.target
    if recipient is None:
        return None
    recipient.apply_status(effect.effect)
    return effect


_APPLIERS: Dict[Type[AppliedEffect], EffectApplierFn] = {
    DamageEffect: _apply_damage,
    PartRepair: _apply_part_repair,
    PartRestore: _apply_part_restore,
    TrapInstall: _apply_trap_install,
    ApplyStatus: _apply_status_effect,
}


def _resolve_applier(effect: AppliedEffect) -> Optional[EffectApplierFn]:
    eff_type = type(effect)
    if applier := _APPLIERS.get(eff_type):
        return applier
    for registered_type, applier in _APPLIERS.items():
        if isinstance(effect, registered_type):
            return applier
    return None


def dispatch_apply(effect: AppliedEffect, ctx: ApplyContext) -> Optional[AppliedEffect]:
    """効果の適用を実行する"""
    applier = _resolve_applier(effect)
    if applier:
        return applier(effect, ctx)
    return effect


def apply_action_effects(
    report: 'ExecutionReport', actor: 'Robot', ctx: Optional['BattleContext'] = None
) -> 'ExecutionReport':
    """適用オブジェクトを世界状態へ反映する。"""
    result = report.result
    target = report.target

    if result is None or not result.success or target is None or not result.applied_effects:
        return report

    apply_ctx = ApplyContext(actor=actor, target=target, battle=ctx)
    applied = []
    for eff in result.applied_effects:
        res = dispatch_apply(eff, apply_ctx)
        applied.append(res if res is not None else eff)

    if tuple(applied) != result.applied_effects:
        updated_result = dataclasses.replace(result, applied_effects=tuple(applied))
        return dataclasses.replace(report, result=updated_result)

    return report