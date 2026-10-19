"""バトルのシミュレーション・計算・ルール適用を統括するマネージャ（シミュレーション専任）。"""
from typing import List, Dict, Optional, Tuple

from domain.constants import ACTIONABLE_PART_TYPES, CommandSlot, PartType, TeamType, GaugeStatus
from domain.models import GameDataProtocol, RobotSetup
from domain.rules import check_battle_end

from .ai_controller import AIController
from .atb_system import ATBSystem
from .constants import BattlePhase
from .context import BattleContext
from .entities.atb_track import ATBEvent
from .entities.commands import BattleCommand, SkipCommand, build_command_for_part
from .entities.part import Part
from .entities.robot import Robot
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
        self.logs = BattleLogBuilder()
        self.atb = ATBSystem(self.ctx.robots)
        self.executor = CommandExecutor(self.ctx, self.targeting, self.logs)

        # 敵AIの初期行動予約
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

    # === シミュレーション制御 ===

    def find_ready_player_robot(self) -> Optional[Robot]:
        """待機状態にある自軍機体を探索する"""
        for robot in self.ctx.robots:
            if robot.team == TeamType.PLAYER and robot.gauge_status == GaugeStatus.READY:
                return robot
        return None

    def setup_attack_declaration(self):
        """行動宣言ログの構築"""
        actor, part = self._get_current_part()
        if not actor or not part:
            return
        if not part.is_implemented:
            action_label = part.action.value if part.action else "未定義"
            self.ctx.set_log([f"err: 未実装の行動形式「{action_label}」"])
        else:
            self.ctx.set_log(self.logs.declaration(actor, part))

    def _get_current_part(self) -> Tuple[Optional[Robot], Optional[Part]]:
        actor = self.ctx.current_actor
        return (actor, actor.current_part) if actor else (None, None)

    def check_battle_end(self) -> bool:
        if self.ctx.winner:
            return True
        snapshots = [r.get_snapshot(i) for i, r in enumerate(self.ctx.robots)]
        is_ended, winner = check_battle_end(snapshots)
        if is_ended:
            self.ctx.winner = winner
        return is_ended

    def handle_charging_interrupts(self) -> bool:
        """充填中の割り込み判定を行い、発生した場合はログ記録とクールダウン移行を実施"""
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

        return interrupted

    def enter_input_phase(self, actor: Robot):
        """指定機体のコマンド入力状態を準備"""
        self.ctx.current_actor = actor
        self.ctx.preview_targets = {
            pt: self.targeting.resolve_preview_target(actor, pt)
            for pt in ACTIONABLE_PART_TYPES
        }

    def update_atb(self, dt: float) -> Optional[BattlePhase]:
        """ATB時間を進行させ、手番発生があれば遷移先フェーズを返す"""
        if self.check_battle_end():
            return None

        self.atb.update(dt)
        turn = self.atb.pop_next_turn()
        if turn is None:
            return None

        actor, event = turn
        self.ctx.current_actor = actor
        if event == ATBEvent.COOLED:
            if actor.team == TeamType.PLAYER:
                self.enter_input_phase(actor)
                return BattlePhase.INPUT
            else:
                self.ai.decide_command(actor)
                return None
        elif event == ATBEvent.CHARGED:
            return self.executor.execute_charged(actor)

        return None

    def apply_execution_result(self) -> bool:
        return self.executor.apply_pending()

    def complete_execution(self):
        self.ctx.current_report = None

    def select_command_slot(self, slot: CommandSlot) -> Optional[BattlePhase]:
        """プレイヤーのコマンド選択を検証・確定し、遷移先フェーズを導出"""
        actor = self.ctx.current_actor
        if not actor or self.ctx.phase != BattlePhase.INPUT:
            return None

        if slot.is_skip:
            return self.submit_player_command(SkipCommand(actor))

        part_type = slot.part_type
        if part_type is None:
            return None

        part = actor.get_part(part_type)
        if not part or not part.can_execute:
            return None

        preview = self.ctx.preview_targets.get(part_type)
        return self.submit_player_command(build_command_for_part(actor, part, preview))

    def submit_player_command(self, command: BattleCommand) -> Optional[BattlePhase]:
        if self.ctx.phase == BattlePhase.INPUT and self.ctx.current_actor:
            self.ctx.current_actor.set_command(command)
            self.ctx.current_actor = None
            return BattlePhase.INITIAL_SETUP if not self.ctx.is_opening_done else BattlePhase.IDLE
        return None