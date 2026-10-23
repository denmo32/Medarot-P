"""予約済みコマンドの実行・解決を担当するエグゼキュータ（シーンフェーズ非依存）。"""
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
from .effect_applier import apply_action_effects
from .log_builder import BattleLogBuilder
from .targeting_resolver import TargetingResolver

if TYPE_CHECKING:
    from ..context import BattleContext


class CommandExecutor:
    """戦闘コマンドの実行解決エンジン。BattlePhase に依存せず純粋な実行結果を返す。"""

    def __init__(
        self,
        ctx: 'BattleContext',
        targeting: TargetingResolver,
        logs: BattleLogBuilder,
        rng: Optional[Callable[[], float]] = None,
    ):
        self.ctx = ctx
        self.targeting = targeting
        self.logs = logs
        self.rng = rng or self.ctx.rng.random

    def execute_charged(self, actor: Robot) -> ExecutionReport:
        """充填完了した機体のコマンドを実行し、結果レポートを作成する。"""
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

        report = self._execute_internal(command)
        all_pre_messages = pre_messages + list(report.pre_messages)

        if report.outcome is ExecutionOutcome.PART_STOPPED:
            part_type = getattr(command, "part_type", "")
            return ExecutionReport(
                outcome=report.outcome,
                pre_messages=all_pre_messages + self.logs.part_stopped(actor, part_type),
            )

        if report.outcome is not ExecutionOutcome.OK:
            return ExecutionReport(
                outcome=report.outcome,
                pre_messages=all_pre_messages + self.logs.execution_failure(actor, command, report.outcome),
            )

        return ExecutionReport(
            outcome=report.outcome,
            result=report.result,
            target=report.target,
            intercepted_by=report.intercepted_by,
            pre_messages=all_pre_messages,
        )

    def _check_trap(self, actor: Robot, part_type: PartType) -> Tuple[List[str], bool]:
        part = actor.get_part(part_type)
        if not part or not part.is_alive:
            return [], False

        triggered_trap = self.ctx.traps.trigger(actor.team, part.action)
        if not triggered_trap:
            return [], False

        _, is_destroyed = actor.apply_damage(part_type, triggered_trap.damage)
        logs = self.logs.trap_triggered(
            actor, part_type, triggered_trap.skill, triggered_trap.damage, is_destroyed
        )
        return logs, is_destroyed

    def apply_execution_result(
        self, actor: Robot, report: ExecutionReport
    ) -> Tuple[ExecutionReport, List[str]]:
        """予約されている行動効果を確定適用し、更新されたレポートとメッセージ一覧を返す"""
        updated_report = apply_action_effects(report, actor, ctx=self.ctx)
        expired_effects = actor.on_action_completed()

        all_messages: List[str] = []
        messages = self.logs.effect_resolution(updated_report.result, updated_report.target)
        if messages:
            all_messages.extend(messages)

        for eff in expired_effects:
            msg = self.logs.effect_expired(actor, eff)
            if msg:
                all_messages.append(msg)

        return updated_report, all_messages

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
                rng=self.ctx.rng,
            )
            result = part.resolve_effect(effect_ctx)
            return ExecutionReport(outcome=ExecutionOutcome.OK, result=result, target=target_robot)

        return ExecutionReport(outcome=ExecutionOutcome.NO_ACTION)

    def _find_interceptor(self, target_robot: Robot) -> Optional[Robot]:
        return next((r for r in self.ctx.robots if r.can_intercept(target_robot)), None)