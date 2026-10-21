"""バトルのシミュレーション・計算・ルール適用を統括するマネージャ（シーンフェーズ非依存）。"""
from typing import List, Dict, Optional, Tuple, Sequence

from domain.constants import ACTIONABLE_PART_TYPES, CommandSlot, PartType, TeamType, GaugeStatus
from domain.models import GameDataProtocol, RobotSetup
from domain.rules import check_battle_end

from .ai_controller import AIController
from .atb_system import ATBSystem
from .context import BattleContext
from .entities.atb_track import ATBEvent
from .entities.commands import (
    BattleCommand,
    ExecutionOutcome,
    ExecutionReport,
    SkipCommand,
    build_command_for_part,
)
from .entities.part import Part
from .entities.robot import Robot
from .events import ATBTurnEvent, PlayerInputRequiredEvent, ActionExecutedEvent
from .execution.command_executor import CommandExecutor
from .execution.log_builder import BattleLogBuilder
from .execution.targeting_resolver import TargetingResolver
from .factory import BattleFactory


class BattleManager:
    """戦闘の純粋シミュレーションエンジン。フェーズ進行は BattleFlow が管轄します。"""

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
        self._logs = BattleLogBuilder()
        self.atb = ATBSystem(self.ctx.robots)
        self.executor = CommandExecutor(self.ctx, self.targeting, self._logs)

        # 敵AIの初期行動予約
        for robot in robots:
            if robot.team == TeamType.ENEMY:
                self.ai.decide_command(robot)

    # === 外部公開プロパティ（カプセル化） ===

    @property
    def current_actor(self) -> Optional[Robot]:
        return self.ctx.current_actor

    @property
    def current_report(self) -> Optional[ExecutionReport]:
        return self.ctx.current_report

    @property
    def robots(self) -> List[Robot]:
        return self.ctx.robots

    @property
    def preview_targets(self) -> Dict[PartType, Optional[Tuple[Robot, Optional[PartType]]]]:
        return self.ctx.preview_targets

    @property
    def is_opening_done(self) -> bool:
        return self.ctx.is_opening_done

    @is_opening_done.setter
    def is_opening_done(self, value: bool):
        self.ctx.is_opening_done = value

    def mark_opening_done(self):
        """オープニング演出完了を記録する"""
        self.ctx.is_opening_done = True

    @property
    def winner(self) -> Optional[TeamType]:
        return self.ctx.winner

    @property
    def battle_log(self) -> Sequence[str]:
        return self.ctx.battle_log

    def find_robot_index(self, robot: Optional[Robot]) -> Optional[int]:
        """指定機体のインデックスを取得する"""
        return self.ctx.find_robot_index(robot)

    def clear_log(self):
        self.ctx.clear_log()

    def set_log(self, messages: Sequence[str]):
        self.ctx.set_log(messages)

    def set_opening_log(self):
        """開戦口上ログを設定する"""
        self.set_log(self._logs.opening())

    def set_declaration_log(self):
        """現在のアクターの行動・技宣言ログを設定する"""
        actor = self.ctx.current_actor
        part = actor.current_part if actor else None
        if not actor or not part:
            return
        if not part.is_implemented:
            action_label = part.action.value if part.action else "未定義"
            self.set_log([f"err: 未実装の行動形式「{action_label}」"])
        else:
            self.set_log(self._logs.declaration(actor, part))

    def set_pierce_log(self):
        """貫通ダメージ発生ログを設定する"""
        self.set_log(self._logs.pierce())

    def set_battle_end_log(self):
        """バトル決着ログを設定する"""
        if self.ctx.winner:
            self.set_log(self._logs.battle_end(self.ctx.winner))

    def get_command_menu_preview_targets(self) -> Dict[PartType, Optional[Tuple[Robot, Optional[PartType]]]]:
        return self.preview_targets

    # === シミュレーション制御 ===

    def find_ready_player_robot(self) -> Optional[Robot]:
        """待機状態にある自軍機体を探索する"""
        for robot in self.ctx.robots:
            if robot.team == TeamType.PLAYER and robot.gauge_status == GaugeStatus.READY:
                return robot
        return None

    def check_battle_end(self) -> bool:
        if self.ctx.winner:
            return True
        snapshots = [r.get_snapshot(i) for i, r in enumerate(self.ctx.robots)]
        is_ended, winner = check_battle_end(snapshots)
        if is_ended:
            self.ctx.winner = winner
        return is_ended

    def detect_charging_interrupts(self) -> List[Tuple[Robot, ExecutionOutcome]]:
        """【純粋シミュレーション】充填中の全機体を自己診断し、
        割り込み対象機体を即座に反転後退させ、(機体, 中断理由) のリストを返す。
        """
        interrupts: List[Tuple[Robot, ExecutionOutcome]] = []
        for robot in self.ctx.robots:
            reason = robot.evaluate_interruption()
            if reason:
                robot.abort_charging_to_cooldown()
                interrupts.append((robot, reason))
        return interrupts

    def handle_charging_interrupts(self) -> List[Tuple[Robot, ExecutionOutcome]]:
        """充填中の全機体を自己診断し、割り込みが発生した機体を反転後退させ、
        割り込みログを設定する。発生した (機体, 中断理由) のリストを返す。
        """
        interrupts = self.detect_charging_interrupts()
        if interrupts:
            messages: List[str] = []
            for robot, reason in interrupts:
                messages.extend(self._logs.interruption(robot, reason))
            self.set_log(messages)
        return interrupts

    def prepare_actor_input(self, actor: Robot):
        """指定機体のコマンド入力状態（予習ターゲット等）を準備する"""
        self.ctx.current_actor = actor
        self.ctx.preview_targets = {
            pt: self.targeting.resolve_preview_target(actor, pt)
            for pt in ACTIONABLE_PART_TYPES
        }

    def update_atb(self, dt: float) -> Optional[ATBTurnEvent]:
        """ATB時間を進行させ、手番発生があればドメインイベントを返す（フェーズ非依存）"""
        if self.check_battle_end():
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
        """放熱完了時の処理：待機状態へ戻し、自軍なら入力要求、敵軍ならAIが即座に予約"""
        actor.enter_ready()
        if actor.team == TeamType.PLAYER:
            self.prepare_actor_input(actor)
            return PlayerInputRequiredEvent(actor=actor)
        else:
            self.ai.decide_command(actor)
            return None

    def _handle_charged(self, actor: Robot) -> Optional[ATBTurnEvent]:
        """充填完了時の処理：コマンド実行を行い、結果イベントを返す"""
        self.ctx.current_actor = actor
        self.ctx.clear_log()
        self.ctx.current_report = None

        report = self.executor.execute_charged(actor)
        if report.pre_messages:
            self.ctx.set_log(report.pre_messages)

        self.ctx.current_report = report
        return ActionExecutedEvent(actor=actor, report=report)

    def apply_execution_result(self) -> List[str]:
        """保留中の行動効果を確定適用し、表示すべきログメッセージ一覧を返す"""
        return self.executor.apply_execution_result()

    def complete_execution(self):
        """行動完了時のクリーンアップ。レポートおよび現在アクターの参照を解除する。"""
        self.ctx.current_report = None
        self.ctx.current_actor = None

    def select_command_slot(self, slot: CommandSlot) -> bool:
        """プレイヤーのコマンド選択を検証・確定する。受理できた場合は True を返す。"""
        actor = self.ctx.current_actor
        if not actor:
            return False

        if slot.is_skip:
            return self.submit_player_command(SkipCommand(actor))

        part_type = slot.part_type
        if part_type is None:
            return False

        if not actor.can_execute_part(part_type):
            return False

        part = actor.get_part(part_type)
        if not part:
            return False

        preview = self.ctx.preview_targets.get(part_type)
        return self.submit_player_command(build_command_for_part(actor, part, preview))

    def submit_player_command(self, command: BattleCommand) -> bool:
        """プレイヤーコマンドをアクター機体に設定する。"""
        actor = self.ctx.current_actor
        if actor:
            actor.set_command(command)
            self.ctx.current_actor = None
            return True
        return False