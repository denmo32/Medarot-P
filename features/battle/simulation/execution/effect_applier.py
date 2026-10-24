# features/battle/execution/effect_applier.py
"""適用オブジェクトを行動結果からバトルの世界状態へ反映するハンドラ。"""
import dataclasses
from typing import Optional, TYPE_CHECKING

from ..entities.commands import ExecutionReport
from .effect_handlers import ApplyContext, dispatch_apply

if TYPE_CHECKING:
    from ..context import BattleContext
    from ..entities.robot import Robot


def apply_action_effects(
    report: ExecutionReport, actor: 'Robot', ctx: Optional['BattleContext'] = None
) -> ExecutionReport:
    """適用オブジェクトを世界状態へ反映する（副作用はディスパッチャ経由のみ）。"""
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