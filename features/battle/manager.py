"""バトルのシミュレーション・計算・ルール適用を統括するマネージャ（シーンフェーズ非依存）。"""
from typing import List, Dict, Optional, Tuple, Sequence

from domain.constants import ACTIONABLE_PART_TYPES, PartType, TeamType, GaugeStatus
from domain.models import GameDataProtocol, RobotSetup
from domain.rules import check_battle_end as eval_battle_end

from .ai_controller import AIController
from .atb_system import ATBSystem
from .context import BattleContext
from .entities.atb_track import ATBEvent
from .entities.commands import (
    BattleCommand,
    ExecutionOutcome,
    SkipCommand,
    build_command_for_part,
)
from .entities.robot import Robot
from .events import ATBTurnEvent, PlayerInputRequiredEvent, ActionExecutedEvent, BattleEndedEvent
from .execution.command_executor import CommandExecutor
from .execution.log_builder import BattleLogBuilder
from .execution.targeting_resolver import TargetingResolver
from .factory import BattleFactory


class BattleManager:
    """戦闘の純粋シミュレーションエンジン。フェーズ進行は BattleDirector が管轄します。"""

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

        # 敵AIの初期行動予約
        for robot in robots:
            if robot.team == TeamType.ENEMY:
                self.ai.decide_command(robot)

    # === 基本プロパティ ===

    @property
    def robots(self) -> List[Robot]:
        return self.ctx.robots

    @property
    def winner(self) -> Optional[TeamType]:
        return self.ctx.winner

    @property
    def battle_log(self) -> Sequence[str]:
        return self.ctx.battle_log

    def find_robot_index(self, robot: Optional[Robot]) -> Optional[int]:
        return self.ctx.find_robot_index(robot)

    def clear_log(self):
        self.ctx.clear_log()

    def set_log(self, messages: Sequence[str]):
        self.ctx.set_log(messages)

    # === シミュレーション制御 ===

    def find_ready_player_robot(self) -> Optional[Robot]:
        for robot in self.ctx.robots:
            if robot.team == TeamType.PLAYER and robot.gauge_status == GaugeStatus.READY:
                return robot
        return None

    def check_battle_end(self) -> bool:
        if self.ctx.winner:
            return True
        is_ended, winner = eval_battle_end(self.ctx.robots)
        if is_ended:
            self.ctx.winner = winner
        return is_ended

    def detect_and_handle_interrupts(self) -> List[str]:
        """充填中の割り込み（予約パーツ破壊・ターゲット喪失）を検出し、放熱へ移行させログを返す"""
        interrupts: List[Tuple[Robot, ExecutionOutcome]] = []
        for robot in self.ctx.robots:
            reason = robot.evaluate_interruption()
            if reason:
                robot.abort_charging_to_cooldown()
                interrupts.append((robot, reason))

        messages: List[str] = []
        for robot, reason in interrupts:
            messages.extend(self.logs.interruption(robot, reason))
        return messages

    def get_preview_targets(self, actor: Robot) -> Dict[PartType, Optional[Tuple[Robot, Optional[PartType]]]]:
        return {
            pt: self.targeting.resolve_preview_target(actor, pt)
            for pt in ACTIONABLE_PART_TYPES
        }

    def update_atb(self, dt: float) -> Optional[ATBTurnEvent]:
        if self.check_battle_end():
            if self.winner:
                return BattleEndedEvent(winner=self.winner)
            return None

        self.atb.update(dt)
        turn = self.atb.pop_next_turn()
        if turn is None:
            return None

        actor, event = turn
        if event == ATBEvent.COOLED:
            return self._handle_cooled(actor)
        elif event == ATBEvent.CHARGED:
            return self._handle_charged(actor)

        return None

    def _handle_cooled(self, actor: Robot) -> Optional[ATBTurnEvent]:
        actor.enter_ready()
        if actor.team == TeamType.PLAYER:
            return PlayerInputRequiredEvent(actor=actor)
        else:
            self.ai.decide_command(actor)
            return None

    def _handle_charged(self, actor: Robot) -> Optional[ATBTurnEvent]:
        report = self.executor.execute_charged(actor)
        return ActionExecutedEvent(actor=actor, report=report)

    def complete_turn(self, actor: Robot):
        actor.finish_execution_to_cooldown()

    def select_command(self, actor: Robot, part_type: Optional[PartType]) -> bool:
        """プレイヤーのコマンド選択（部位指定、またはスキップ=None）を検証・確定する"""
        if part_type is None:
            return self.submit_player_command(actor, SkipCommand(actor))

        if not actor.can_execute_part(part_type):
            return False

        part = actor.get_part(part_type)
        if not part:
            return False

        preview = self.targeting.resolve_preview_target(actor, part_type)
        return self.submit_player_command(actor, build_command_for_part(actor, part, preview))

    def submit_player_command(self, actor: Robot, command: BattleCommand) -> bool:
        actor.set_command(command)
        return True