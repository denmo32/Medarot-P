"""戦闘シーケンスを yield（ジェネレータ）で統括するディレクター。"""
import logging
from typing import Any, Generator, Optional
from domain.constants import SkillPresentation
from features.battle.constants import BattleTiming
from features.battle.entities.commands import ExecutionOutcome, ExecutionReport
from features.battle.entities.robot import Robot
from features.battle.events import ActionExecutedEvent, BattleEndedEvent, PlayerInputRequiredEvent
from features.battle.manager import BattleManager
from features.battle.staging.directives import (
    AdvanceCutinPierce,
    Await,
    AwaitCutin,
    AwaitHpAnimation,
    AwaitNextTurn,
    AwaitPlayerInput,
    AwaitTime,
    AwaitUserConfirm,
    ClearCutin,
    ClearRadar,
    Directive,
    SetOpeningPopupVisible,
    ShowLog,
    StageDamage,
    StartCutin,
    StartRadar,
)
from features.battle.staging.visual_coordinator import VisualCoordinator

logger = logging.getLogger(__name__)

_MAX_COROUTINE_STEPS = 100


class BattleDirector:
    """戦闘の演出・進行手続きを一元管理するスケジューラ"""

    def __init__(self, manager: BattleManager, visual: VisualCoordinator):
        self.manager = manager
        self.visual = visual

        self.pending_await: Optional[Await] = None
        self._send_value: Any = None
        self.opening_popup_visible: bool = False
        self.is_finished: bool = False

        self._routine: Optional[Generator] = self._run_battle()
        self._step()

    # === 外部公開プロパティ ===

    @property
    def current_player_input_await(self) -> Optional[AwaitPlayerInput]:
        return self.pending_await if isinstance(self.pending_await, AwaitPlayerInput) else None

    @property
    def can_user_confirm(self) -> bool:
        return isinstance(self.pending_await, AwaitUserConfirm)

    @property
    def is_game_over(self) -> bool:
        return self.manager.winner is not None and self.is_finished

    # === フレーム進行と入力 ===

    def advance(self):
        """完了済みの Await を消費し、コルーチンを次の待機点まで進める"""
        if self.pending_await is not None and self.pending_await.is_done(self):
            self._send_value = self.pending_await.take_result()
            self.pending_await = None
            self._step()

    def tick(self, dt: float):
        """論理時間を進行させ、待機が完了したら即座に次へ進める"""
        if self.pending_await is not None:
            self.pending_await.tick(dt, self)
            self.advance()

    def handle_input(self, input_state) -> bool:
        """入力を待機オブジェクトに委任し、条件が満たされたら進行させる"""
        if self.pending_await is not None:
            handled = self.pending_await.handle_input(input_state, self)
            if handled:
                self.advance()
                return True
        return False

    def _step(self):
        """コルーチンを次の未完了 Await まで一気に進める（無限ループ保護付き）"""
        if self._routine is None:
            return

        steps = 0
        try:
            while steps < _MAX_COROUTINE_STEPS:
                steps += 1
                item = self._routine.send(self._send_value)
                self._send_value = None

                if isinstance(item, Await):
                    self.pending_await = item
                    if self.pending_await.is_done(self):
                        self._send_value = self.pending_await.take_result()
                        self.pending_await = None
                        continue
                    break
                elif isinstance(item, Directive):
                    self._execute_directive(item)
            else:
                logger.error("コルーチンの1フレーム消化ステップ数が上限 (%d) を超えました。", _MAX_COROUTINE_STEPS)
        except StopIteration:
            self._routine = None
            self.pending_await = None
            self.is_finished = True

    def _execute_directive(self, d: Directive):
        if isinstance(d, ShowLog):
            self.manager.set_log(d.messages)
        elif isinstance(d, StartRadar):
            self.visual.start_radar(d.attacker_index, d.target_index)
        elif isinstance(d, ClearRadar):
            self.visual.clear_radar()
        elif isinstance(d, StartCutin):
            self.visual.start_cutin(d.actor, d.target, d.part, d.report)
        elif isinstance(d, StageDamage):
            self.visual.stage_damage(d.report)
            self.visual.update_cutin_report(d.report)
        elif isinstance(d, AdvanceCutinPierce):
            self.visual.advance_damage_step(d.target)
            self.visual.advance_cutin()
        elif isinstance(d, ClearCutin):
            self.visual.clear_cutin()
        elif isinstance(d, SetOpeningPopupVisible):
            self.opening_popup_visible = d.visible

    # ==========================================================================
    # コルーチン本体（戦闘のライフサイクル）
    # ==========================================================================

    def _run_battle(self) -> Generator:
        # 1. 開戦・初期コマンド入力・オープニング演出
        yield from self._run_opening()

        # 2. メインATBバトルループ
        while not self.manager.winner:
            turn_event = yield AwaitNextTurn()
            if isinstance(turn_event, BattleEndedEvent):
                break

            if isinstance(turn_event, PlayerInputRequiredEvent):
                yield from self._run_player_input(turn_event.actor)
            elif isinstance(turn_event, ActionExecutedEvent):
                yield from self._run_action(turn_event.actor, turn_event.report)

        # 3. 決着演出
        yield from self._run_battle_end()

    def _run_opening(self) -> Generator:
        while ready_robot := self.manager.find_ready_player_robot():
            yield from self._run_player_input(ready_robot)

        yield ShowLog(self.manager.logs.opening())
        yield AwaitUserConfirm()

        yield SetOpeningPopupVisible(True)
        yield AwaitTime(BattleTiming.OPENING_POPUP, can_skip=True)
        yield SetOpeningPopupVisible(False)

        self.manager.clear_log()

    def _run_player_input(self, actor: Robot) -> Generator:
        preview_targets = self.manager.get_preview_targets(actor)
        slot = yield AwaitPlayerInput(actor=actor, preview_targets=preview_targets)
        if slot:
            self.manager.select_command_slot(actor, slot)

    def _run_action(self, actor: Robot, report: ExecutionReport) -> Generator:
        part = actor.current_part

        # 行動不能・トラップ被弾等の不発処理
        if report.outcome is not ExecutionOutcome.OK:
            if report.pre_messages:
                yield ShowLog(report.pre_messages)
                yield AwaitUserConfirm()
            yield from self._finalize_turn(actor)
            return

        # 1. ターゲットレーダー演出
        if report.target:
            actor_idx = self.manager.find_robot_index(actor)
            target_idx = self.manager.find_robot_index(report.target)
            if actor_idx is not None and target_idx is not None:
                yield StartRadar(actor_idx, target_idx)
                yield AwaitTime(BattleTiming.TARGET_INDICATION)

        # 2. 技・行動の宣言ログ
        if part:
            yield ShowLog(self.manager.logs.declaration(actor, part))
            yield AwaitUserConfirm()

        # 3. 演出とダメージ適用
        if part and part.presentation == SkillPresentation.CUTIN and report.target:
            yield StartCutin(actor, report.target, part, report)
            yield AwaitCutin()

            updated_report, messages = self.manager.apply_execution_result(actor, report)
            yield StageDamage(updated_report)
            if messages:
                yield ShowLog(messages)
            yield AwaitUserConfirm()

            if updated_report.has_pierce and updated_report.target:
                yield ShowLog(self.manager.logs.pierce())
                yield AdvanceCutinPierce(updated_report.target)
                yield AwaitHpAnimation()
                yield AwaitUserConfirm()

            yield ClearCutin()

        elif part and part.presentation == SkillPresentation.LOG_ONLY:
            updated_report, messages = self.manager.apply_execution_result(actor, report)
            yield StageDamage(updated_report)
            if messages:
                yield ShowLog(messages)
            yield AwaitHpAnimation()
            yield AwaitUserConfirm()
        else:
            updated_report, _ = self.manager.apply_execution_result(actor, report)
            yield StageDamage(updated_report)
            yield AwaitHpAnimation()

        # レーダー終了とターンの総合後処理
        yield ClearRadar()
        yield from self._finalize_turn(actor)

    def _finalize_turn(self, actor: Robot) -> Generator:
        # この瞬間にアクターを放熱（クールダウン）へ移行させる（責務の集約）
        self.manager.complete_turn(actor)

        # ターン終了時に描画モデルのHP目標値を論理モデルと確定同期
        self.visual.sync_all_targets()

        # 勝敗判定
        if self.manager.check_battle_end():
            return

        # 割り込みチェック（充填中機体のターゲット喪失など）
        interrupts = self.manager.handle_charging_interrupts()
        if interrupts:
            yield AwaitUserConfirm()

        self.manager.clear_log()

    def _run_battle_end(self) -> Generator:
        if self.manager.winner:
            yield ShowLog(self.manager.logs.battle_end(self.manager.winner))
            yield AwaitUserConfirm()