# features/battle/simulation/execution/effect_applier.py
"""行動結果をバトルの世界状態（Robot/Trap）へ反映するハンドラ。"""
import dataclasses
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..context import BattleContext
    from ..entities.commands import ExecutionReport
    from ..entities.robot import Robot


def apply_action_effects(
    report: 'ExecutionReport',
    actor: 'Robot',
    ctx: Optional['BattleContext'] = None,
) -> 'ExecutionReport':
    """行動結果を世界状態（機体HP・状態・トラップ）へ即座に反映する。"""
    result = report.result
    target = report.target

    if result is None or not result.success:
        return report

    # 1. 主ダメージ
    updated_primary = result.primary_damage
    if updated_primary and target:
        actual_dmg, destroyed = target.apply_damage(updated_primary.part_type, updated_primary.amount)
        updated_primary = dataclasses.replace(updated_primary, effective_damage=actual_dmg, destroyed=destroyed)

    # 2. 貫通ダメージ
    updated_pierce = result.pierce_damage
    if updated_pierce and target:
        actual_dmg, destroyed = target.apply_damage(updated_pierce.part_type, updated_pierce.amount)
        updated_pierce = dataclasses.replace(updated_pierce, effective_damage=actual_dmg, destroyed=destroyed)

    # 3. 回復・復元
    updated_repair = result.repair_result
    if updated_repair and target:
        if updated_repair.is_restored:
            restored = target.apply_restore(updated_repair.part_type)
            if restored is None:
                updated_repair = None
        else:
            res = target.apply_repair(updated_repair.amount, updated_repair.part_type)
            if res is not None:
                updated_repair = dataclasses.replace(updated_repair, amount=res[1])
            else:
                updated_repair = None

    # 4. 状態異常・バフ付与
    if result.status_effect:
        recipient = actor if result.status_to_self else target
        if recipient:
            recipient.apply_status(result.status_effect)

    # 5. トラップ設置
    updated_trap = result.installed_trap
    if updated_trap and ctx and target:
        installed = dataclasses.replace(
            updated_trap, target_team=target.team, source_name=actor.name
        )
        ctx.traps.install(installed)
        updated_trap = installed

    updated_result = dataclasses.replace(
        result,
        primary_damage=updated_primary,
        pierce_damage=updated_pierce,
        repair_result=updated_repair,
        installed_trap=updated_trap,
    )
    return dataclasses.replace(report, result=updated_result)