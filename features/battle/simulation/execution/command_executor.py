"""予約済みコマンドの確定解決を担当するエグゼキュータ。"""
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING

from domain.combat import resolve_attack
from domain.combat_formulas import get_best_guard_part
from domain.constants import PartType, SkillKind
from domain.models import EffectResolutionContext

from ..entities.commands import (
    BattleCommand,
    ExecutionOutcome,
    ExecutionReport,
    PartCommand,
    SkipCommand,
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
        """充填完了した機体のコマンドを実行・適用し、結果レポートを作成する。"""
        actor.start_execution()

        command = actor.current_command
        if isinstance(command, SkipCommand):
            return ExecutionReport(
                outcome=ExecutionOutcome.SKIPPED,
                pre_messages=self.logs.skipped(actor),
            )

        pre_messages: List[str] = []
        if isinstance(command, PartCommand):
            trap_logs, is_destroyed = self._check_trap(actor, command.part_type)
            pre_messages.extend(trap_logs)
            if is_destroyed:
                fail_logs = self.logs.execution_failure(actor, command, ExecutionOutcome.TRAP_DESTROYED)
                return ExecutionReport(
                    outcome=ExecutionOutcome.TRAP_DESTROYED,
                    pre_messages=trap_logs + fail_logs,
                )

        initial_report = self._execute_internal(command)
        all_pre_messages = pre_messages + list(initial_report.pre_messages)

        if initial_report.outcome is not ExecutionOutcome.OK:
            fail_logs = self.logs.execution_failure(actor, command, initial_report.outcome)
            return ExecutionReport(
                outcome=initial_report.outcome,
                pre_messages=all_pre_messages + fail_logs,
            )

        # 結果メッセージの生成（世界状態への適用は演出タイミングに合わせて Manager が行う）
        result_messages: List[str] = []
        messages = self.logs.effect_resolution(initial_report.result, initial_report.target)
        if messages:
            result_messages.extend(messages)

        return ExecutionReport(
            outcome=initial_report.outcome,
            result=initial_report.result,
            target=initial_report.target,
            intercepted_by=initial_report.intercepted_by,
            pre_messages=all_pre_messages,
            result_messages=result_messages,
        )

    def _check_trap(self, actor: Robot, part_type: PartType) -> Tuple[List[str], bool]:
        part = actor.get_part(part_type)
        if not part or not part.is_alive:
            return [], False

        triggered_trap = self.manager.traps.trigger(actor.team, part.action)
        if not triggered_trap:
            return [], False

        _, is_destroyed = actor.apply_damage(part_type, triggered_trap.damage)
        logs = self.logs.trap_triggered(
            actor, part_type, triggered_trap.skill, triggered_trap.damage, is_destroyed
        )
        return logs, is_destroyed

    def _execute_internal(self, command: Optional[BattleCommand]) -> ExecutionReport:
        if isinstance(command, SkipCommand):
            return ExecutionReport(outcome=ExecutionOutcome.SKIPPED)
        if isinstance(command, PartCommand):
            return self._execute_part_command(command)
        return ExecutionReport(outcome=ExecutionOutcome.NO_ACTION)

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