# features/battle/staging/director.py
"""戦闘シーケンスを yield（待機条件のみ）で統括するディレクター。"""
import logging
from typing import Any, Dict, Generator, List, Optional, Sequence, Tuple
from domain.constants import COMMAND_MENU_PART_ORDER, SkillPresentation
from core.inputs import InputState
from features.battle.constants import BattleTiming
from features.battle.input.command_menu_navigation import resolve_command_menu_navigation
from features.battle.presentation.command_menu_builder import build_command_menu_items
from features.battle.simulation.entities.commands import ExecutionOutcome, ExecutionReport
from features.battle.simulation.entities.robot import Robot
from features.battle.simulation.events import ActionExecutedEvent, BattleEndedEvent, PlayerInputRequiredEvent
from features.battle.simulation.manager import BattleManager
from features.battle.staging.cutin_director import CutinDirector
from features.battle.staging.directives import (
    Await,
    AwaitCutin,
    AwaitHpAnimation,
    AwaitNextTurn,
    AwaitPlayerInput,
    AwaitTime,
    AwaitUserConfirm,
)
from features.battle.staging.target_radar_director import TargetRadarDirector
from features.battle.staging.visual_state import RobotVisualState
from features.battle.ui.layout import hit_test_command_menu

logger = logging.getLogger(__name__)

_MAX_COROUTINE_STEPS = 100


class BattleDirector:
    """戦闘の演出・進行手続き・視覚状態を一元管理するスケジューラ"""

    def __init__(self, manager: BattleManager, skip_staging: bool = False):
        self.manager = manager
        self.skip_staging = skip_staging

        # 演出用アクティブメッセージ
        self.active_messages: List[str] = []

        # 視覚演出状態（Coordinator を廃止し直接保持）
        self.visual_states: Dict[Robot, RobotVisualState] = {
            r: RobotVisualState(r) for r in self.manager.robots
        }
        self.cutin: Optional[CutinDirector] = None
        self.radar: Optional[TargetRadarDirector] = None

        self.pending_await: Optional[Await] = None
        self._send_value: Any = None
        self.opening_popup_visible: bool = False
        self.is_finished: bool = False
        self._selected_command_index: int = 0

        self._routine: Optional[Generator] = self._run_battle()
        self._step()

    # === メッセージ管理 ===

    def set_messages(self, messages: Sequence[str]):
        self.active_messages = list(messages)

    def clear_messages(self):
        self.active_messages.clear()

    # === プロパティ・演出クエリ ===

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

    def is_hp_animating(self) -> bool:
        return any(vs.is_hp_animating for vs in self.visual_states.values())

    def is_combat_active(self, robot: Robot) -> bool:
        return self.cutin is not None and self.cutin.is_combatant(robot)

    # === 演出制御 ===

    def start_cutin(self, actor: Robot, target: Robot, part: Any, report: ExecutionReport):
        self.cutin = CutinDirector(actor=actor, target=target, part=part, report=report)

    def advance_cutin(self):
        if self.cutin:
            self.cutin.advance()

    def is_cutin_finished(self) -> bool:
        return self.cutin is None or self.cutin.is_animation_finished

    def clear_cutin(self):
        self.cutin = None

    def start_radar(self, attacker_index: int, target_index: int):
        self.radar = TargetRadarDirector(attacker_index, target_index)

    def clear_radar(self):
        self.radar = None

    # === 進行更新 ===

    def _advance(self, send_val: Any = None):
        self._send_value = send_val
        self.pending_await = None
        self._step()

    def tick(self, dt: float):
        for vs in self.visual_states.values():
            vs.update(dt)

        if self.radar:
            self.radar.update(dt)

        if self.pending_await is None:
            return

        await_item = self.pending_await

        if isinstance(await_item, AwaitTime):
            await_item.remaining = max(0.0, await_item.remaining - dt)
            if await_item.remaining <= 0.0:
                self._advance()

        elif isinstance(await_item, AwaitCutin):
            if self.cutin:
                self.cutin.update(dt)
            if self.is_cutin_finished():
                self._advance()

        elif isinstance(await_item, AwaitHpAnimation):
            if not self.is_hp_animating():
                self._advance()

        elif isinstance(await_item, AwaitNextTurn):
            turn = self.manager.update_atb(dt)
            if turn is not None:
                self._advance(send_val=turn)

    def handle_input(self, input_state: InputState, screen_size: Optional[Tuple[int, int]] = None) -> bool:
        """キーボードおよびマウス入力を一元処理する"""
        if self.pending_await is None:
            return False

        await_item = self.pending_await

        if isinstance(await_item, AwaitUserConfirm):
            if (input_state.btn_ok or input_state.mouse_clicked) and not self.is_hp_animating():
                self._advance()
                return True

        elif isinstance(await_item, AwaitTime):
            if await_item.can_skip and (input_state.btn_ok or input_state.mouse_clicked):
                await_item.remaining = 0.0
                self._advance()
                return True

        elif isinstance(await_item, AwaitCutin):
            if input_state.btn_ok or input_state.mouse_clicked:
                self.advance_cutin()
                self._advance()
                return True

        elif isinstance(await_item, AwaitPlayerInput):
            # マウスクリック処理（解像度情報がある場合）
            if input_state.mouse_clicked and screen_size is not None:
                new_idx, confirmed = hit_test_command_menu(
                    screen_size,
                    (input_state.mouse_x, input_state.mouse_y),
                    len(await_item.menu_items),
                    self._selected_command_index,
                )
                if 0 <= new_idx < len(await_item.selectable_mask) and await_item.selectable_mask[new_idx]:
                    self._selected_command_index = new_idx
                    if confirmed:
                        chosen_part = await_item.menu_items[new_idx].part_type
                        self._advance(send_val=chosen_part)
                        return True

            # 十字キー・決定キーナビゲーション
            self._selected_command_index = resolve_command_menu_navigation(
                self._selected_command_index, input_state, await_item.selectable_mask
            )
            if input_state.btn_ok and await_item.selectable_mask[self._selected_command_index]:
                chosen_part = await_item.menu_items[self._selected_command_index].part_type
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
                    # === スキップモード時は演出系 Await を即時バイパス ===
                    if self.skip_staging and isinstance(item, (AwaitTime, AwaitUserConfirm, AwaitCutin, AwaitHpAnimation)):
                        continue

                    self.pending_await = item
                    if isinstance(item, AwaitHpAnimation) and not self.is_hp_animating():
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

    # === シーケンスコルーチン ===

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

        self.set_messages(self.manager.logs.opening())
        yield AwaitUserConfirm()

        self.opening_popup_visible = True
        yield AwaitTime(BattleTiming.OPENING_POPUP, can_skip=True)
        self.opening_popup_visible = False

        self.clear_messages()

    def _run_player_input(self, actor: Robot) -> Generator:
        self._selected_command_index = 0
        preview_targets = self.manager.get_preview_targets(actor)
        menu_items = build_command_menu_items(actor, preview_targets, self.manager.robots)

        selected_part = yield AwaitPlayerInput(
            actor=actor,
            menu_items=menu_items,
        )
        precomputed = preview_targets.get(selected_part) if selected_part else None
        self.manager.select_command(actor, selected_part, precomputed_target=precomputed)

    def _run_action(self, actor: Robot, report: ExecutionReport) -> Generator:
        part = actor.current_part

        # 1. トラップ発動ステップ（あれば）
        if report.trap_trigger:
            if report.trap_trigger.messages:
                self.set_messages(report.trap_trigger.messages)
                yield AwaitUserConfirm()
            self.manager.apply_trap_action(actor, report.trap_trigger)
            yield AwaitHpAnimation()

            if report.outcome == ExecutionOutcome.TRAP_DESTROYED:
                if report.pre_messages:
                    self.set_messages(report.pre_messages)
                    yield AwaitUserConfirm()
                yield from self._finalize_turn(actor)
                return

        # 2. 不発・失敗時
        if report.outcome is not ExecutionOutcome.OK:
            if report.pre_messages:
                self.set_messages(report.pre_messages)
                yield AwaitUserConfirm()
            yield from self._finalize_turn(actor)
            return

        # 3. ターゲティング & 宣言ステップ
        # 機体狙いではない技（targets_part=False のトラップ等）はレーダーを描画しない
        should_show_radar = bool(report.target and (part is None or part.targets_part))
        if should_show_radar:
            actor_idx = self.manager.find_robot_index(actor)
            target_idx = self.manager.find_robot_index(report.target)
            if actor_idx is not None and target_idx is not None:
                self.start_radar(actor_idx, target_idx)
                yield AwaitTime(BattleTiming.TARGET_INDICATION)

        if part:
            self.set_messages(self.manager.logs.declaration(actor, part))
            yield AwaitUserConfirm()

        # 4. 主行動の演出 & HPコミット
        is_cutin = bool(part and part.presentation == SkillPresentation.CUTIN and report.target)
        if is_cutin:
            self.start_cutin(actor, report.target, part, report)
            yield AwaitCutin()

        # 主効果を世界状態へコミット
        self.manager.apply_primary_action(report, actor)

        if report.result_messages:
            self.set_messages(report.result_messages)

        yield AwaitHpAnimation()
        yield AwaitUserConfirm()

        # 5. 貫通演出 & HPコミット（あれば）
        if report.has_pierce and report.target:
            self.set_messages(self.manager.logs.pierce())
            self.manager.apply_pierce_action(report)
            if is_cutin:
                self.advance_cutin()
            yield AwaitHpAnimation()
            yield AwaitUserConfirm()

        # クリーンアップ
        self.clear_cutin()
        self.clear_radar()

        yield from self._finalize_turn(actor)

    def _finalize_turn(self, actor: Robot) -> Generator:
        self.manager.complete_turn(actor)

        if self.manager.check_battle_end():
            return

        interrupt_logs = self.manager.detect_and_handle_interrupts()
        if interrupt_logs:
            self.set_messages(interrupt_logs)
            yield AwaitUserConfirm()

        self.clear_messages()

    def _run_battle_end(self) -> Generator:
        if self.manager.winner:
            self.set_messages(self.manager.logs.battle_end(self.manager.winner))
            yield AwaitUserConfirm()