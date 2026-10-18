"""予約済みコマンドの実行・解決・中断判定を担当するエグゼキュータ。"""
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING

from domain.combat import resolve_attack
from domain.combat_formulas import get_best_guard_part
from domain.constants import PartType, SkillKind
from domain.models import EffectResolutionContext

from ..constants import BattlePhase
from ..entities.commands import (
    BattleCommand,
    ExecutionOutcome,
    ExecutionReport,
    PartCommand,
    SkipCommand,
)
from ..entities.robot import Robot
from .effect_applier import apply_action_to_world
from .log_builder import BattleLogBuilder
from .targeting_resolver import TargetingResolver

if TYPE_CHECKING:
    from ..context import BattleContext


class CommandExecutor:
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

    def execute_charged(self, actor: Robot) -> BattlePhase:
        actor.start_execution()
        self.ctx.clear_log()
        self.ctx.current_report = None

        command = actor.current_command
        if isinstance(command, SkipCommand):
            actor.enter_cooldown()
            self.ctx.set_log(self.logs.skipped(actor))
            return BattlePhase.LOG_WAIT

        pre_messages: List[str] = []
        if isinstance(command, PartCommand):
            trap_logs, is_destroyed = self._check_trap(actor, command.part_type)
            pre_messages.extend(trap_logs)
            if is_destroyed:
                self.ctx.set_log(
                    trap_logs + self.logs.execution_failure(actor, command, ExecutionOutcome.PART_UNUSABLE)
                )
                actor.enter_cooldown(interrupted=False)
                return BattlePhase.LOG_WAIT

        report = self._execute_internal(command)
        if pre_messages:
            report = ExecutionReport(
                outcome=report.outcome,
                result=report.result,
                target=report.target,
                intercepted_by=report.intercepted_by,
                pre_messages=pre_messages + list(report.pre_messages),
            )

        if report.outcome is ExecutionOutcome.PART_STOPPED:
            part_type = getattr(command, "part_type", "")
            self.ctx.set_log(pre_messages + self.logs.part_stopped(actor, part_type))
            actor.enter_cooldown(interrupted=False)
            return BattlePhase.LOG_WAIT

        if report.outcome is not ExecutionOutcome.OK:
            self.ctx.set_log(pre_messages + self.logs.execution_failure(actor, command, report.outcome))
            actor.enter_cooldown(interrupted=True)
            return BattlePhase.LOG_WAIT

        self.ctx.current_report = report
        return BattlePhase.TARGET_INDICATION

    def _check_trap(self, actor: Robot, part_type: PartType) -> Tuple[List[str], bool]:
        triggered_trap, is_destroyed = actor.trigger_trap_if_applicable(self.ctx.traps)
        if not triggered_trap:
            return [], False
        logs = self.logs.trap_triggered(
            actor, part_type, triggered_trap.skill, triggered_trap.damage, is_destroyed
        )
        return logs, is_destroyed

    def apply_pending(self) -> bool:
        report = self.ctx.current_report
        actor = self.ctx.current_actor
        if report is None or actor is None:
            return self.ctx.has_log

        updated_report, expired_effects = apply_action_to_world(report, actor, ctx=self.ctx)
        self.ctx.current_report = updated_report
        actor.enter_cooldown()

        messages = self.logs.effect_resolution(updated_report.result, updated_report.target)
        if messages is not None:
            self.ctx.set_log(messages)

        for eff in expired_effects:
            msg = self.logs.effect_expired(actor, eff)
            if msg:
                self.ctx.append_log(msg)

        return self.ctx.has_log

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

        target_robot, target_part_type = self.targeting.resolve_execution_target(actor, command.part_type)
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
        """味方機体のうち身代わり（ブロック）可能な機体を探索する"""
        return next((r for r in self.ctx.robots if r.can_intercept(target_robot)), None)