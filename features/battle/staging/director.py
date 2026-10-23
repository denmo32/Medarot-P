# features/battle/staging/director.py
"""戦闘シーケンスを yield（ジェネレータ）で統括するディレクター。"""
import logging
from typing import Any, Generator, Optional
from domain.constants import SkillPresentation
from features.battle.constants import BattleTiming
from features.battle.entities.commands import ExecutionOutcome, ExecutionReport
from features.battle.entities.robot import Robot
from features.battle.events import ActionExecutedEvent, BattleEndedEvent, PlayerInputRequiredEvent
from features.battle.manager import BattleManager
from features.battle.presentation.command_menu_builder import build_command_menu_items
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

    @property
    def current_player_input_await(self) -> Optional[AwaitPlayerInput]:
        return self.pending_await if isinstance(self.pending_await, AwaitPlayerInput) else None

    @property
    def can_user_confirm(self) -> bool:
        return isinstance(self.pending_await, AwaitUserConfirm)

    @property
    def is_game_over(self) -> bool:
        return self.manager.winner is not None and self.is_finished

    def advance(self):
        if self.pending_await is not None and self.pending_await.is_done(self):
            self._send_value = self.pending_await.take_result()
            self.pending_await = None
            self._step()

    def tick(self, dt: float):
        if self.pending_await is not None:
            self.pending_await.tick(dt, self)
            self.advance()

    def handle_input(self, input_state) -> bool:
        if self.pending_await is not None:
            handled = self.pending_await.handle_input(input_state, self)
            if handled:
                self.advance()
                return True
        return False

    def _step(self):
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
            self.visual.stage_primary_damage(d.report)
        elif isinstance(d, AdvanceCutinPierce):
            self.visual.stage_pierce_damage(d.report)
            self.visual.advance_cutin()
        elif isinstance(d, ClearCutin):
            self.visual.clear_cutin()
        elif isinstance(d, SetOpeningPopupVisible):
            self.opening_popup_visible = d.visible

    def _run_battle(self) -> Generator:
        yield from self._run_opening()

        while not self.manager.winner:
            turn_event = yield AwaitNextTurn()
            if isinstance(turn_event, BattleEndedEvent):
                break

            if isinstance(turn_event, PlayerInputRequiredEvent):
                yield from self._run_player_input(turn_event.actor)
            elif isinstance(turn_event, ActionExecutedEvent):
                yield from self._run_action(turn_event.actor, turn_event.report)

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
        items = build_command_menu_items(actor, preview_targets, self.manager.robots)
        selected_part = yield AwaitPlayerInput(actor=actor, preview_targets=preview_targets, items=items)
        precomputed = preview_targets.get(selected_part) if selected_part else None
        self.manager.select_command(actor, selected_part, precomputed_target=precomputed)

    def _run_action(self, actor: Robot, report: ExecutionReport) -> Generator:
        part = actor.current_part

        # 失敗・不発時
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

        # 3. 行動演出の解決（カットイン / ログのみ / その他）
        is_cutin = bool(part and part.presentation == SkillPresentation.CUTIN and report.target)
        if is_cutin:
            yield StartCutin(actor, report.target, part, report)
            yield AwaitCutin()

        # ダメージステージングと結果ログ
        yield StageDamage(report)
        if report.result_messages:
            yield ShowLog(report.result_messages)

        if not is_cutin:
            yield AwaitHpAnimation()
        yield AwaitUserConfirm()

        # 貫通演出
        if is_cutin:
            if report.has_pierce and report.target:
                yield ShowLog(self.manager.logs.pierce())
                yield AdvanceCutinPierce(report)
                yield AwaitHpAnimation()
                yield AwaitUserConfirm()
            yield ClearCutin()

        # レーダー終了とターンの総合後処理
        yield ClearRadar()
        yield from self._finalize_turn(actor)

    def _finalize_turn(self, actor: Robot) -> Generator:
        self.manager.complete_turn(actor)
        self.visual.sync_all_targets()

        if self.manager.check_battle_end():
            return

        interrupt_logs = self.manager.detect_and_handle_interrupts()
        if interrupt_logs:
            yield ShowLog(interrupt_logs)
            yield AwaitUserConfirm()

        self.manager.clear_log()

    def _run_battle_end(self) -> Generator:
        if self.manager.winner:
            yield ShowLog(self.manager.logs.battle_end(self.manager.winner))
            yield AwaitUserConfirm()