# features/battle/simulation/manager.py
"""バトルのシミュレーション・計算・状態更新を統括するマネージャ。"""
import dataclasses
import random
from typing import List, Dict, Optional, Tuple, Sequence

from domain.constants import ACTIONABLE_PART_TYPES, PartType, TeamType, GaugeStatus
from domain.models import GameDataProtocol, RobotSetup
from domain.rules import check_battle_end as eval_battle_end
from domain.traps import TrapManager

from .ai_controller import AIController
from .atb_system import ATBSystem
from .entities.atb_track import ATBEvent
from .entities.commands import (
    BattleCommand,
    ExecutionOutcome,
    ExecutionReport,
    SkipCommand,
    TrapTriggerResult,
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
        auto_battle: bool = False,
    ):
        self.robots: List[Robot] = BattleFactory.create_robots(player_setups, enemy_setups, data_manager)
        self.seed = seed if seed is not None else random.randrange(2**32)
        self.rng = random.Random(self.seed)
        self.winner: Optional[TeamType] = None
        self.traps = TrapManager()
        self.auto_battle = auto_battle

        self.targeting = TargetingResolver(self)
        self.ai = AIController(self, self.targeting)
        self.logs = BattleLogBuilder()
        self.atb = ATBSystem(self.robots)
        self.executor = CommandExecutor(self, self.targeting, self.logs)

        # 敵AI（およびオート戦闘時はプレイヤーも）の初期行動予約
        for robot in self.robots:
            if robot.team == TeamType.ENEMY or self.auto_battle:
                self.ai.decide_command(robot)

    # === 基本プロパティ・検索 ===

    def find_robot_index(self, robot: Optional[Robot]) -> Optional[int]:
        if robot is None:
            return None
        for idx, candidate in enumerate(self.robots):
            if candidate is robot:
                return idx
        return None

    # === 行動結果の世界状態への段階的適用（演出と完全に同期） ===

    def apply_trap_action(self, actor: Robot, trap_trigger: TrapTriggerResult):
        """トラップ発動によるダメージとトラップ消費を世界状態へ反映する"""
        if trap_trigger.trap:
            self.traps.consume(trap_trigger.trap)
        actor.apply_damage(trap_trigger.part_type, trap_trigger.damage)

    def apply_primary_action(self, report: ExecutionReport, actor: Robot):
        """行動の主効果（ダメージ・回復・状態異常・トラップ等）を世界状態へ反映する"""
        result = report.result
        target = report.target
        if result is None or not result.success:
            return

        # 1. 主ダメージ
        if result.primary_damage and target:
            target.apply_damage(result.primary_damage.part_type, result.primary_damage.amount)

        # 2. 回復・復元
        if result.repair_result and target:
            rep = result.repair_result
            if rep.is_restored:
                target.apply_restore(rep.part_type)
            else:
                target.apply_repair(rep.amount, rep.part_type)

        # 3. 状態異常・バフ付与
        if result.status_effect:
            recipient = actor if result.status_to_self else target
            if recipient:
                recipient.apply_status(result.status_effect)

        # 4. トラップ設置
        if result.installed_trap and target:
            installed = dataclasses.replace(
                result.installed_trap, source_name=actor.name
            )
            self.traps.install(installed)

        # 攻撃バフの消費
        actor.on_action_completed()

    def apply_pierce_action(self, report: ExecutionReport):
        """貫通ダメージを世界状態へ反映する"""
        result = report.result
        target = report.target
        if result and result.pierce_damage and target:
            target.apply_damage(result.pierce_damage.part_type, result.pierce_damage.amount)

    # === シミュレーション制御 ===

    def find_ready_player_robot(self) -> Optional[Robot]:
        if self.auto_battle:
            return None
        for robot in self.robots:
            if robot.team == TeamType.PLAYER and robot.gauge_status == GaugeStatus.READY:
                return robot
        return None

    def check_battle_end(self) -> bool:
        if self.winner:
            return True
        is_ended, winner = eval_battle_end(self.robots)
        if is_ended:
            self.winner = winner
        return is_ended

    def detect_and_handle_interrupts(self) -> List[str]:
        """充填中の割り込み（予約パーツ破壊・ターゲット喪失）を検出し、放熱へ移行させログを返す"""
        interrupts: List[Tuple[Robot, ExecutionOutcome]] = []
        for robot in self.robots:
            reason = robot.evaluate_interruption()
            if reason:
                robot.abort_charging_to_cooldown()
                interrupts.append((robot, reason))

        messages: List[str] = []
        for robot, reason in interrupts:
            messages.extend(self.logs.interruption(robot, reason))
        return messages

    def get_preview_targets(self, actor: Robot) -> Dict[PartType, Optional[Tuple[Robot, Optional[PartType]]]]:
        """アクターの各パーツのプレビュー対象を一括取得"""
        return {
            pt: self.targeting.resolve_preview_target(actor, pt)
            for pt in ACTIONABLE_PART_TYPES
        }

    def update_atb(self, dt: float) -> Optional[ATBTurnEvent]:
        """バトルの時間進行（効果タイマー更新 + ATB進行）を一元管理"""
        if self.check_battle_end():
            if self.winner:
                return BattleEndedEvent(winner=self.winner)
            return None

        # 状態異常・バフの時間進行（充填中・放熱中の機体のみ）
        for robot in self.robots:
            robot.tick_effects(dt)

        # ATB ゲージ進行
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
        if actor.team == TeamType.PLAYER and not self.auto_battle:
            return PlayerInputRequiredEvent(actor=actor)
        else:
            self.ai.decide_command(actor)
            return None

    def _handle_charged(self, actor: Robot) -> Optional[ATBTurnEvent]:
        report = self.executor.execute_charged(actor)
        return ActionExecutedEvent(actor=actor, report=report)

    def complete_turn(self, actor: Robot):
        actor.finish_execution_to_cooldown()

    def select_command(
        self,
        actor: Robot,
        part_type: Optional[PartType],
        precomputed_target: Optional[Tuple[Robot, Optional[PartType]]] = None,
    ) -> bool:
        """プレイヤーのコマンド選択（部位指定、またはスキップ=None）を検証・確定する"""
        if part_type is None:
            return self.submit_player_command(actor, SkipCommand(actor))

        part = actor.get_part(part_type)
        if not part or not part.can_execute:
            return False

        target = precomputed_target or self.targeting.resolve_preview_target(actor, part_type)
        return self.submit_player_command(actor, build_command_for_part(actor, part, target))

    def submit_player_command(self, actor: Robot, command: BattleCommand) -> bool:
        actor.set_command(command)
        return True