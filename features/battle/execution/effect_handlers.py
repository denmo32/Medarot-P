# features/battle/execution/effect_handlers.py
"""適用オブジェクトの反映ロジックとログ生成仕様を一元管理するモジュール（OCP準拠）。"""
import dataclasses
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Type, TYPE_CHECKING

from domain.constants import EffectType, TeamType
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

if TYPE_CHECKING:
    from ..context import BattleContext
    from ..entities.robot import Robot


@dataclass
class ApplyContext:
    actor: 'Robot'
    target: Optional['Robot'] = None
    battle: Optional['BattleContext'] = None


EffectApplierFn = Callable[[AppliedEffect, ApplyContext], Optional[AppliedEffect]]
EffectLoggerFn = Callable[[AppliedEffect, 'Robot'], List[str]]


@dataclass(frozen=True)
class EffectSpec:
    """効果の適用とログ生成をペアにした定義仕様"""
    apply: EffectApplierFn
    format_log: EffectLoggerFn


# === 適用ハンドラ群 ===

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


# === ログ生成ハンドラ群 ===

def _log_repair(effect: AppliedEffect, target: 'Robot') -> List[str]:
    assert isinstance(effect, PartRepair)
    return [f"{target.name}の{effect.part_type.label}が {effect.amount} 回復した！"]


def _log_restore(effect: AppliedEffect, target: 'Robot') -> List[str]:
    assert isinstance(effect, PartRestore)
    return [f"{target.name}の{effect.part_type.label}が復元された！"]


def _log_trap_install(effect: AppliedEffect, target: 'Robot') -> List[str]:
    assert isinstance(effect, TrapInstall)
    team_label = "味方チーム" if target.team == TeamType.PLAYER else "相手チーム"
    return [f"{team_label}に「{effect.trap.skill.value}」が設置された！"]


def _log_apply_status(effect: AppliedEffect, target: 'Robot') -> List[str]:
    assert isinstance(effect, ApplyStatus)
    eff = effect.effect
    name = target.name
    if eff.type == EffectType.STOP:
        label = eff.part_type.label if eff.part_type else ""
        return [f"{name}の{label}が停止した！" if label else f"{name}が停止した！"]
    if eff.type == EffectType.BLOCK:
        return [f"{name}は味方への攻撃を庇う！"]
    if eff.type == EffectType.PROTECT:
        return [f"{name}はダメージを減少する！"]
    if eff.type == EffectType.SUCCESS_UP:
        return [f"{name}の命中度が上がった！ 残り{eff.charges}回"]
    return []


def _no_log(effect: AppliedEffect, target: 'Robot') -> List[str]:
    return []


# === 単一管理テーブル（新しい効果はここに1行追加するだけ） ===

EFFECT_SPECS: Dict[Type[AppliedEffect], EffectSpec] = {
    PartDamage: EffectSpec(apply=_apply_damage, format_log=_no_log),
    PierceDamage: EffectSpec(apply=_apply_damage, format_log=_no_log),
    PartRepair: EffectSpec(apply=_apply_part_repair, format_log=_log_repair),
    PartRestore: EffectSpec(apply=_apply_part_restore, format_log=_log_restore),
    TrapInstall: EffectSpec(apply=_apply_trap_install, format_log=_log_trap_install),
    ApplyStatus: EffectSpec(apply=_apply_status_effect, format_log=_log_apply_status),
}


def dispatch_apply(effect: AppliedEffect, ctx: ApplyContext) -> Optional[AppliedEffect]:
    """効果の適用を実行する"""
    spec = EFFECT_SPECS.get(type(effect))
    if spec:
        return spec.apply(effect, ctx)
    return effect


def dispatch_format_log(effect: AppliedEffect, target: 'Robot') -> List[str]:
    """効果に対するログ文言を生成する"""
    spec = EFFECT_SPECS.get(type(effect))
    if spec:
        return spec.format_log(effect, target)
    return []