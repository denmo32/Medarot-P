"""適用オブジェクトを行動結果からバトルの世界状態へ反映するハンドラ。

この層が「副作用の唯一の発生点」である。純粋な計算結果（`ActionResult`）を
受け取り、演出の完了後に初めて機体へ状態の確定を命じる（Tell, Don't Ask）。
主攻撃ダメージ・貫通ダメージ・修復・状態異常はすべて同一のハンドラレジストリを
通るため、新しい効果の追加は「適用オブジェクト + 1 行登録」で閉じる（OCP）。
"""
import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple, Type

from domain.effect_payloads import (
    AppliedEffect,
    ApplyStatus,
    PartDamage,
    PartRepair,
    PartRestore,
    PierceDamage,
    TrapInstall,
)
from domain.models import StatusEffect

if TYPE_CHECKING:
    from .commands import ExecutionReport
    from .context import BattleContext
    from .models import Robot


@dataclass
class ApplyContext:
    actor: 'Robot'
    target: Optional['Robot'] = None
    battle: Optional['BattleContext'] = None


EffectHandler = Callable[[AppliedEffect, ApplyContext], Optional[AppliedEffect]]


def _apply_part_damage(effect: PartDamage, ctx: ApplyContext) -> Optional[AppliedEffect]:
    """主攻撃ダメージの確定反映。apply_damage の戻り値から破壊状況を直接取得する。"""
    if ctx.target is None:
        return None
    actual_dmg, destroyed = ctx.target.apply_damage(effect.part_type, effect.amount)
    return dataclasses.replace(effect, effective_damage=actual_dmg, destroyed=destroyed)


def _apply_pierce_damage(effect: PierceDamage, ctx: ApplyContext) -> Optional[AppliedEffect]:
    """貫通ダメージの確定反映。主攻撃と同一の経路で適用する。"""
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
    PartDamage: _apply_part_damage,
    PierceDamage: _apply_pierce_damage,
    PartRepair: _apply_part_repair,
    PartRestore: _apply_part_restore,
    TrapInstall: _apply_trap_install,
    ApplyStatus: _apply_status_effect,
}


def apply_action_to_world(
    report: 'ExecutionReport', actor: 'Robot', ctx: Optional['BattleContext'] = None
) -> Tuple['ExecutionReport', List[StatusEffect]]:
    """行動結果の付随効果を確定反映し、機体に事後処理（回数制バフ消費等）を委譲する"""
    result = report.result
    target = report.target

    updated_report = report
    if result is not None and result.success and target is not None and result.applied_effects:
        apply_ctx = ApplyContext(actor=actor, target=target, battle=ctx)
        applied = []
        for eff in result.applied_effects:
            handler = EFFECT_HANDLERS.get(type(eff))
            if handler:
                res = handler(eff, apply_ctx)
                if res:
                    applied.append(res)
        if applied != result.applied_effects:
            updated_result = dataclasses.replace(result, applied_effects=applied)
            updated_report = dataclasses.replace(report, result=updated_result)

    # 【Tell, Don't Ask】コマンドやパーツ種別を外部で判定せず、機体に完了後処理を命じる
    expired_effects = actor.on_action_completed()

    return updated_report, expired_effects