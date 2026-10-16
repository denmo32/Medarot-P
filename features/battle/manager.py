"""バトルの全体進行、フェーズ遷移、ルール適用を統括するマネージャ。"""
from typing import List, Dict, Optional, Tuple

from domain.constants import ACTIONABLE_PART_TYPES, CommandSlot, PartType, TeamType, GaugeStatus, SkillPresentation
from domain.models import GameDataProtocol, RobotSetup
from domain.rules import check_battle_end

from .atb_system import ATBEvent, ATBSystem
from .commands import BattleCommand, SkipCommand, build_command_for_part
from .ai_controller import AIController
from .command_executor import CommandExecutor
from .constants import BattlePhase, INTERRUPTIBLE_PHASES, PHASE_CONFIGS
from .context import BattleContext
from .factory import BattleFactory
from .log_builder import BattleLogBuilder
from .models import Robot, Part
from .presentation.presentation import BattlePresentation
from .presentation.cutin_director import CutinEvent
from .targeting_resolver import TargetingResolver


class BattleManager:
    def __init__(
        self,
        player_setups: List[RobotSetup],
        enemy_setups: List[RobotSetup],
        data_manager: GameDataProtocol,
        seed: Optional[int] = None,
    ):
        robots = BattleFactory.create_robots(player_setups, enemy_setups, data_manager)
        self.ctx = BattleContext(robots, seed=seed)

        self.targeting = TargetingResolver(self.ctx)
        self.ai = AIController(self.ctx, self.targeting)
        self.logs = BattleLogBuilder()
        self.atb = ATBSystem(self.ctx.robots)
        self.executor = CommandExecutor(self.ctx, self.targeting, self.logs)
        self.presentation = BattlePresentation(self.ctx.robots)

        self.change_phase(BattlePhase.INITIAL_SETUP)

        for robot in robots:
            if robot.team == TeamType.ENEMY:
                self.ai.decide_command(robot)

    @property
    def phase(self) -> BattlePhase:
        return self.ctx.phase

    @property
    def current_actor(self) -> Optional[Robot]:
        return self.ctx.current_actor

    @property
    def robots(self) -> List[Robot]:
        return self.ctx.robots

    def get_command_menu_preview_targets(self) -> Dict[PartType, Optional[Tuple[Robot, Optional[PartType]]]]:
        return self.ctx.preview_targets

    def change_phase(self, new_phase: BattlePhase):
        self.ctx.phase = new_phase
        config = PHASE_CONFIGS.get(new_phase)
        self.presentation.start_phase_timer(config.duration if config else 0.0)

        if new_phase == BattlePhase.OPENING_LOG:
            self.ctx.set_log(self.logs.opening())
        elif new_phase == BattlePhase.ATTACK_DECLARATION:
            self._enter_attack_declaration()

    def advance_phase(self):
        if self.presentation.is_busy():
            return

        phase = self.ctx.phase
        if phase == BattlePhase.OPENING_POPUP:
            self.ctx.is_opening_done = True
            self.ctx.clear_log()
            self.change_phase(BattlePhase.IDLE)
        elif phase == BattlePhase.ATTACK_DECLARATION:
            self._advance_attack_declaration()
        elif phase in (BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT):
            self._handle_cutin_advance()
        elif phase == BattlePhase.LOG_WAIT:
            self.complete_execution()
        else:
            config = PHASE_CONFIGS.get(phase)
            if config and config.next_phase:
                self.change_phase(config.next_phase)

    def _handle_cutin_advance(self):
        if not self.presentation.cutin_director:
            self.complete_execution()
            return

        for event in self.presentation.advance_cutin():
            if event == CutinEvent.ANIMATION_FINISHED:
                self.apply_execution_result()
                self.change_phase(BattlePhase.CUTIN_RESULT)
            elif event == CutinEvent.PIERCE_ADVANCED:
                self.ctx.set_log(["貫通ダメージ！"])
                report = self.ctx.current_report
                if report and report.target:
                    self.presentation.advance_damage_step(report.target)
            elif event == CutinEvent.COMPLETED:
                self.complete_execution()

    def update(self, dt: float):
        self.presentation.update(dt)

        if self.ctx.phase in (
            BattlePhase.CUTIN,
            BattlePhase.CUTIN_RESULT,
            BattlePhase.LOG_WAIT,
            BattlePhase.GAME_OVER,
        ):
            self._update_phase(dt)
            return

        if self._check_battle_end():
            if not self.presentation.is_hp_animating():
                self.complete_execution()
            return

        self._handle_charging_interrupts()
        self._update_phase(dt)

    def _update_phase(self, dt: float):
        phase = self.ctx.phase
        if phase == BattlePhase.INITIAL_SETUP:
            for robot in self.ctx.robots:
                if robot.team == TeamType.PLAYER and robot.gauge_status == GaugeStatus.READY:
                    self.enter_input_phase(robot)
                    return
            self.change_phase(BattlePhase.OPENING_LOG if not self.ctx.is_opening_done else BattlePhase.IDLE)
        elif phase == BattlePhase.IDLE:
            self.update_atb(dt)
        elif phase == BattlePhase.CUTIN:
            events = self.presentation.update_cutin(dt)
            if events:
                for event in events:
                    if event == CutinEvent.ANIMATION_FINISHED:
                        self.apply_execution_result()
                        self.change_phase(BattlePhase.CUTIN_RESULT)
            elif not self.presentation.cutin_director:
                self.apply_execution_result()
                self.change_phase(BattlePhase.CUTIN_RESULT)
        elif phase in (BattlePhase.OPENING_POPUP, BattlePhase.TARGET_INDICATION):
            if self.presentation.is_timer_expired():
                config = PHASE_CONFIGS.get(phase)
                next_phase = config.next_phase if config else None
                if next_phase is None:
                    return
                if phase == BattlePhase.OPENING_POPUP:
                    self.advance_phase()
                else:
                    self.change_phase(next_phase)

    def _enter_attack_declaration(self):
        actor, part = self._get_current_part()
        if not actor or not part:
            return
        if not part.is_implemented:
            action_label = part.action.value if part.action else "未定義"
            self.ctx.set_log([f"err: 未実装の行動形式「{action_label}」"])
        else:
            self.ctx.set_log(self.logs.declaration(actor, part))

    def _advance_attack_declaration(self):
        actor, part = self._get_current_part()
        if not actor or not part or not part.is_implemented:
            if actor:
                actor.enter_cooldown(interrupted=False)
            self.complete_execution()
            return

        presentation = part.presentation
        if presentation == SkillPresentation.CUTIN:
            report = self.ctx.current_report
            if report and report.result:
                self.presentation.start_cutin(part, report)
            self.change_phase(BattlePhase.CUTIN)
        elif presentation == SkillPresentation.LOG_ONLY:
            if self.apply_execution_result():
                self.change_phase(BattlePhase.LOG_WAIT)
            else:
                self.complete_execution()
        else:
            self.apply_execution_result()
            self.complete_execution()

    def _get_current_part(self) -> Tuple[Optional[Robot], Optional[Part]]:
        actor = self.ctx.current_actor
        return (actor, actor.current_part) if actor else (None, None)

    def _check_battle_end(self) -> bool:
        if self.ctx.winner:
            return True
        snapshots = [r.get_snapshot(i) for i, r in enumerate(self.ctx.robots)]
        is_ended, winner = check_battle_end(snapshots)
        if is_ended:
            self.ctx.winner = winner
        return is_ended

    def _handle_charging_interrupts(self):
        if self.presentation.is_hp_animating() or self.ctx.phase not in INTERRUPTIBLE_PHASES:
            return

        interrupted = False
        for robot in self.ctx.robots:
            interrupt_reason = robot.evaluate_interruption()
            if not interrupt_reason:
                continue

            messages = self.logs.interruption(robot, interrupt_reason)
            if not interrupted:
                self.ctx.set_log(messages)
                interrupted = True
            else:
                self.ctx.extend_log(messages)
            robot.enter_cooldown(interrupted=True)

        if interrupted:
            self.change_phase(BattlePhase.LOG_WAIT)

    def enter_input_phase(self, actor: Robot):
        self.ctx.current_actor = actor
        self.ctx.preview_targets = {
            pt: self.targeting.resolve_preview_target(actor, pt)
            for pt in ACTIONABLE_PART_TYPES
        }
        self.change_phase(BattlePhase.INPUT)

    def is_hp_animating(self) -> bool:
        return self.presentation.is_hp_animating()

    def is_waiting_for_advance(self) -> bool:
        return self.presentation.is_waiting_for_advance(self.ctx.phase)

    def update_atb(self, dt: float):
        if self._check_battle_end():
            if not self.presentation.is_hp_animating():
                self.complete_execution()
            return

        self.atb.update(dt)
        turn = self.atb.pop_next_turn()
        if turn is None:
            return

        actor, event = turn
        self.ctx.current_actor = actor
        if event == ATBEvent.COOLED:
            if actor.team == TeamType.PLAYER:
                self.enter_input_phase(actor)
            else:
                self.ai.decide_command(actor)
        elif event == ATBEvent.CHARGED:
            self.change_phase(self.executor.execute_charged(actor))

    def apply_execution_result(self) -> bool:
        applied = self.executor.apply_pending()
        report = self.ctx.current_report

        if report:
            self.presentation.stage_damage(report)

        if report and report.result:
            self.presentation.update_cutin_result(report.result)

        return applied

    def complete_execution(self):
        self.presentation.sync_all_targets()
        self.presentation.clear_cutin()
        self.ctx.current_report = None

        if self._check_battle_end():
            if not self.ctx.result_announced:
                self.ctx.result_announced = True
                self.ctx.set_log(self.logs.battle_end(self.ctx.winner))
                self.change_phase(BattlePhase.LOG_WAIT)
            else:
                self.change_phase(BattlePhase.GAME_OVER)
        else:
            self.ctx.clear_log()
            self.change_phase(BattlePhase.IDLE)

    def select_command_slot(self, slot: CommandSlot):
        actor = self.ctx.current_actor
        if not actor or self.ctx.phase != BattlePhase.INPUT:
            return

        if slot.is_skip:
            self.submit_player_command(SkipCommand(actor))
            return

        part_type = slot.part_type
        if part_type is None:
            return

        part = actor.get_part(part_type)
        if not part or not part.can_execute:
            return

        preview = self.ctx.preview_targets.get(part_type)
        self.submit_player_command(build_command_for_part(actor, part, preview))

    def submit_player_command(self, command: BattleCommand):
        if self.ctx.phase == BattlePhase.INPUT and self.ctx.current_actor:
            self.ctx.current_actor.set_command(command)
            self.ctx.current_actor = None
            self.change_phase(BattlePhase.INITIAL_SETUP if not self.ctx.is_opening_done else BattlePhase.IDLE)