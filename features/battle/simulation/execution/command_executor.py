"""予約済みコマンドの確定解決を担当するエグゼキュータ。"""
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING

from domain.combat import resolve_attack
from domain.combat_formulas import get_best_guard_part
from domain.constants import PartType, SkillKind
from domain.models import EffectResolutionContext

from ..entities.commands import (
    ExecutionOutcome,
    ExecutionReport,
    PartCommand,
    SkipCommand,
    TrapTriggerResult,
)
from ..entities.robot import Robot
from .log_builder import BattleLogBuilder
from .targeting_resolver import TargetingResolver

if TYPE_CHECKING:
    from ..manager import BattleManager


class CommandExecutor:
    """戦闘コマンドの実行解決エンジン。"""

    def __init__(
        self,
        manager: 'BattleManager',
        targeting: TargetingResolver,
        logs: BattleLogBuilder,
        rng: Optional[Callable[[], float]] = None,
    ):
        self.manager = manager
        self.targeting = targeting
        self.logs = logs
        self.rng = rng or self.manager.rng.random

    def execute_charged(self, actor: Robot) -> ExecutionReport:
        """充填完了した機体のコマンドを実行し、結果レポートを作成する。"""
        actor.start_execution()
        command = actor.current_command

        if isinstance(command, SkipCommand):
            return ExecutionReport(
                outcome=ExecutionOutcome.SKIPPED,
                pre_messages=self.logs.skipped(actor),
            )

        if not isinstance(command, PartCommand):
            return ExecutionReport(outcome=ExecutionOutcome.NO_ACTION)

        # 1. トラップ判定（純粋計算・副作用なし）
        trap_trigger = self._check_trap(actor, command.part_type)
        if trap_trigger and trap_trigger.is_destroyed:
            fail_logs = self.logs.execution_failure(actor, command, ExecutionOutcome.TRAP_DESTROYED)
            return ExecutionReport(
                outcome=ExecutionOutcome.TRAP_DESTROYED,
                trap_trigger=trap_trigger,
                pre_messages=fail_logs,
            )

        # 2. パーツコマンドの実行
        report = self._execute_part_command(command)

        if report.outcome is not ExecutionOutcome.OK:
            fail_logs = self.logs.execution_failure(actor, command, report.outcome)
            return ExecutionReport(
                outcome=report.outcome,
                trap_trigger=trap_trigger,
                pre_messages=list(report.pre_messages) + fail_logs,
            )

        # 3. 成功時メッセージの生成
        result_messages = list(self.logs.effect_resolution(report.result, report.target))

        return ExecutionReport(
            outcome=report.outcome,
            result=report.result,
            target=report.target,
            intercepted_by=report.intercepted_by,
            trap_trigger=trap_trigger,
            pre_messages=list(report.pre_messages),
            result_messages=result_messages,
        )

    def _check_trap(self, actor: Robot, part_type: PartType) -> Optional[TrapTriggerResult]:
        part = actor.get_part(part_type)
        if not part or not part.is_alive:
            return None

        triggered_trap = self.manager.traps.find_triggered(actor.team, part.action)
        if not triggered_trap:
            return None

        is_destroyed = (part.hp <= triggered_trap.damage)
        logs = self.logs.trap_triggered(
            actor, part_type, triggered_trap.skill, triggered_trap.damage, is_destroyed
        )
        return TrapTriggerResult(
            trap_skill=triggered_trap.skill,
            part_type=part_type,
            damage=triggered_trap.damage,
            is_destroyed=is_destroyed,
            trap=triggered_trap,
            messages=logs,
        )

    def _execute_part_command(self, command: PartCommand) -> ExecutionReport:
        actor = command.actor
        part, outcome = actor.validate_actionable_part(command.part_type)
        if part is None:
            return ExecutionReport(outcome=outcome)

        target_robot, target_part_type = self.targeting.resolve_execution_target(command)
        if not target_robot:
            return ExecutionReport(outcome=ExecutionOutcome.TARGET_LOST)

        attacker_p = actor.to_participant(part)

        if part.skill_kind == SkillKind.ATTACK:
            if not target_part_type:
                return ExecutionReport(outcome=ExecutionOutcome.TARGET_LOST)

            intercepted_by = self._find_interceptor(target_robot)
            if intercepted_by:
                actual_target = intercepted_by
                resolved_target_part = get_best_guard_part(actual_target.get_parts_hp())
            else:
                actual_target = target_robot
                resolved_target_part = target_part_type

            result = resolve_attack(
                attacker=attacker_p,
                target=actual_target.to_participant(),
                target_part_type=resolved_target_part,
                rng=self.rng,
            )
            return ExecutionReport(
                outcome=ExecutionOutcome.OK, result=result, target=actual_target, intercepted_by=intercepted_by
            )

        elif part.skill_kind == SkillKind.EFFECT:
            effect_ctx = EffectResolutionContext.from_participants(
                attacker=attacker_p,
                target=target_robot.to_participant(),
                source_part_type=command.part_type,
                target_part_type=target_part_type,
                target_parts_max_hp=target_robot.get_parts_max_hp(),
                rng=self.manager.rng,
            )
            result = part.resolve_effect(effect_ctx)
            return ExecutionReport(outcome=ExecutionOutcome.OK, result=result, target=target_robot)

        return ExecutionReport(outcome=ExecutionOutcome.NO_ACTION)

    def _find_interceptor(self, target_robot: Robot) -> Optional[Robot]:
        return next((r for r in self.manager.robots if r.can_intercept(target_robot)), None)