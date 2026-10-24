# features/battle/staging/director.py
"""戦闘シーケンスを yield（待機条件のみ）で統括するディレクター。"""
import logging
from typing import Any, Generator, Optional
from domain.constants import COMMAND_MENU_PART_ORDER, SkillPresentation
from features.battle.constants import BattleTiming
from features.battle.input.command_menu_navigation import resolve_command_menu_navigation
from features.battle.simulation.entities.commands import (
    ExecutionOutcome,
    ExecutionReport,
    build_command_menu_selectable_mask,
)
from features.battle.simulation.entities.robot import Robot
from features.battle.simulation.events import ActionExecutedEvent, BattleEndedEvent, PlayerInputRequiredEvent
from features.battle.simulation.manager import BattleManager
from features.battle.staging.directives import (
    Await,
    AwaitCutin,
    AwaitHpAnimation,
    AwaitNextTurn,
    AwaitPlayerInput,
    AwaitTime,
    AwaitUserConfirm,
)
from features.battle.staging.visual_coordinator import VisualCoordinator

logger = logging.getLogger(__name__)

_MAX_COROUTINE_STEPS = 100


class BattleDirector:
    """戦闘の演出・進行手続きを一元管理するスケジューラ"""

    def __init__(self, manager: BattleManager, visual: VisualCoordinator, skip_staging: bool = False):
        self.manager = manager
        self.visual = visual
        self.skip_staging = skip_staging

        self.pending_await: Optional[Await] = None
        self._send_value: Any = None
        self.opening_popup_visible: bool = False
        self.is_finished: bool = False
        self._selected_command_index: int = 0

        self._routine: Optional[Generator] = self._run_battle()
        self._step()

    @property
    def current_player_input_await(self) -> Optional[AwaitPlayerInput]:
        return self.pending_await if isinstance(self.pending_await, AwaitPlayerInput) else None

    @property
    def selected_command_index(self) -> int:
        return self._selected_command_index

    @property
    def can_user_confirm(self) -> bool:
        return isinstance(self.pending_await, AwaitUserConfirm)

    @property
    def is_game_over(self) -> bool:
        return self.manager.winner is not None and self.is_finished

    def handle_command_menu_mouse(self, new_index: int, confirmed: bool) -> bool:
        """マウスヒットテスト結果に基づく選択カーソル移動および決定"""
        if not isinstance(self.pending_await, AwaitPlayerInput):
            return False

        mask = self.pending_await.selectable_mask
        if 0 <= new_index < len(mask) and mask[new_index]:
            self._selected_command_index = new_index
            if confirmed:
                chosen_part = COMMAND_MENU_PART_ORDER[new_index]
                self._advance(send_val=chosen_part)
                return True
        return False

    def _advance(self, send_val: Any = None):
        self._send_value = send_val
        self.pending_await = None
        self._step()

    def tick(self, dt: float):
        if self.pending_await is None:
            return

        await_item = self.pending_await

        if isinstance(await_item, AwaitTime):
            await_item.remaining = max(0.0, await_item.remaining - dt)
            if await_item.remaining <= 0.0:
                self._advance()

        elif isinstance(await_item, AwaitCutin):
            self.visual.update_cutin(dt)
            if self.visual.is_cutin_finished():
                self._advance()

        elif isinstance(await_item, AwaitHpAnimation):
            if not self.visual.is_hp_animating():
                self._advance()

        elif isinstance(await_item, AwaitNextTurn):
            turn = self.manager.update_atb(dt)
            if turn is not None:
                self._advance(send_val=turn)

    def handle_input(self, input_state) -> bool:
        if self.pending_await is None:
            return False

        await_item = self.pending_await

        if isinstance(await_item, AwaitUserConfirm):
            if (input_state.btn_ok or input_state.mouse_clicked) and not self.visual.is_hp_animating():
                self._advance()
                return True

        elif isinstance(await_item, AwaitTime):
            if await_item.can_skip and (input_state.btn_ok or input_state.mouse_clicked):
                await_item.remaining = 0.0
                self._advance()
                return True

        elif isinstance(await_item, AwaitCutin):
            if input_state.btn_ok or input_state.mouse_clicked:
                self.visual.advance_cutin()
                self._advance()
                return True

        elif isinstance(await_item, AwaitPlayerInput):
            self._selected_command_index = resolve_command_menu_navigation(
                self._selected_command_index, input_state, await_item.selectable_mask
            )
            if input_state.btn_ok and await_item.selectable_mask[self._selected_command_index]:
                chosen_part = COMMAND_MENU_PART_ORDER[self._selected_command_index]
                self._advance(send_val=chosen_part)
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
                    if isinstance(item, AwaitHpAnimation) and not self.visual.is_hp_animating():
                        self.pending_await = None
                        continue
                    if isinstance(item, AwaitTime) and item.remaining <= 0.0:
                        self.pending_await = None
                        continue
                    break
            else:
                logger.error("コルーチンの1フレーム消化ステップ数が上限 (%d) を超えました。", _MAX_COROUTINE_STEPS)
        except StopIteration:
            self._routine = None
            self.pending_await = None
            self.is_finished = True

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

        if not self.skip_staging:
            self.manager.set_log(self.manager.logs.opening())
            yield AwaitUserConfirm()

            self.opening_popup_visible = True
            yield AwaitTime(BattleTiming.OPENING_POPUP, can_skip=True)
            self.opening_popup_visible = False

        self.manager.clear_log()

    def _run_player_input(self, actor: Robot) -> Generator:
        self._selected_command_index = 0
        preview_targets = self.manager.get_preview_targets(actor)
        selectable_mask = build_command_menu_selectable_mask(actor, preview_targets)
        selected_part = yield AwaitPlayerInput(
            actor=actor,
            preview_targets=preview_targets,
            selectable_mask=selectable_mask,
        )
        precomputed = preview_targets.get(selected_part) if selected_part else None
        self.manager.select_command(actor, selected_part, precomputed_target=precomputed)

    def _run_action(self, actor: Robot, report: ExecutionReport) -> Generator:
        part = actor.current_part

        # 失敗・不発時
        if report.outcome is not ExecutionOutcome.OK:
            if not self.skip_staging and report.pre_messages:
                self.manager.set_log(report.pre_messages)
                yield AwaitUserConfirm()
            yield from self._finalize_turn(actor)
            return

        # 1. ターゲットレーダー演出
        if not self.skip_staging and report.target:
            actor_idx = self.manager.find_robot_index(actor)
            target_idx = self.manager.find_robot_index(report.target)
            if actor_idx is not None and target_idx is not None:
                self.visual.start_radar(actor_idx, target_idx)
                yield AwaitTime(BattleTiming.TARGET_INDICATION)

        # 2. 技・行動の宣言ログ
        if not self.skip_staging and part:
            self.manager.set_log(self.manager.logs.declaration(actor, part))
            yield AwaitUserConfirm()

        # 3. 行動演出の解決（カットイン / ログのみ / その他）
        is_cutin = bool(part and part.presentation == SkillPresentation.CUTIN and report.target)
        if not self.skip_staging and is_cutin:
            self.visual.start_cutin(actor, report.target, part, report)
            yield AwaitCutin()

        # ダメージ反映（内部目標HPへの反映は演出スキップ時も必ず行う）
        self.visual.stage_primary_damage(report)

        if not self.skip_staging:
            if report.result_messages:
                self.manager.set_log(report.result_messages)

            if not is_cutin:
                yield AwaitHpAnimation()
            yield AwaitUserConfirm()

            # 貫通演出
            if is_cutin:
                if report.has_pierce and report.target:
                    self.manager.set_log(self.manager.logs.pierce())
                    self.visual.stage_pierce_damage(report)
                    self.visual.advance_cutin()
                    yield AwaitHpAnimation()
                    yield AwaitUserConfirm()
                self.visual.clear_cutin()

            # レーダー終了
            self.visual.clear_radar()
        else:
            # スキップ時は即座に全ターゲットHPを同期
            self.visual.sync_all_targets()

        yield from self._finalize_turn(actor)

    def _finalize_turn(self, actor: Robot) -> Generator:
        self.manager.complete_turn(actor)
        self.visual.sync_all_targets()

        if self.manager.check_battle_end():
            return

        interrupt_logs = self.manager.detect_and_handle_interrupts()
        if interrupt_logs:
            if not self.skip_staging:
                self.manager.set_log(interrupt_logs)
                yield AwaitUserConfirm()

        self.manager.clear_log()

    def _run_battle_end(self) -> Generator:
        if self.manager.winner:
            self.manager.set_log(self.manager.logs.battle_end(self.manager.winner))
            yield AwaitUserConfirm()