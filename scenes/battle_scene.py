"""バトル画面のシーン（型付き遷移・集約入力駆動・決定論的RNG・演出とロジックの調停）"""
import random
from typing import Optional
from core.scene_manager import Scene, SceneTransition
from core.constants import SceneId
from domain.constants import SkillPresentation
from features.battle.constants import BattlePhase, PHASE_CONFIGS
from features.battle.factory import BattleFactory
from features.battle.presentation.command_menu_builder import (
    build_command_menu_items,
    to_selectable_mask,
)
from features.battle.presentation.view_builder import BattleViewBuilder
from features.battle.input.command_menu_navigation import resolve_command_menu_navigation
from features.battle.manager import BattleManager
from features.battle.staging.cutin_director import CutinEvent
from features.battle.staging.visual_coordinator import VisualCoordinator
from ui.battle.layout import hit_test_command_menu
from ui.battle.renderer import BattleRenderer


class BattleScene(Scene):
    def __init__(self, ctx, seed: Optional[int] = None):
        super().__init__(ctx)
        self.seed = seed if seed is not None else random.randrange(2**32)
        battle_rng = random.Random(self.seed)

        player_setups = BattleFactory.get_player_setups(ctx.save_manager)
        enemy_setups = BattleFactory.get_enemy_setups(ctx.data_manager, rng=battle_rng)

        # 1. 純粋ロジック (BattleManager)
        self.manager = BattleManager(player_setups, enemy_setups, ctx.data_manager, seed=self.seed)
        # 2. 演出進行 (VisualCoordinator)
        self.visual = VisualCoordinator(self.manager.ctx.robots)
        # 3. 表示モデル構築 (ViewBuilder)
        self.view_builder = BattleViewBuilder(self.manager.ctx, self.visual)
        # 4. レンダラー (Renderer)
        self.renderer = BattleRenderer(self.screen) if self.screen is not None else None

        self.selected_button_index = 0
        self._last_phase: Optional[BattlePhase] = None

    def handle_input(self, input_state) -> SceneTransition:
        phase = self.manager.phase

        if input_state.btn_menu:
            return SceneTransition.to(SceneId.TITLE)

        if phase == BattlePhase.INPUT:
            self._handle_input_phase(input_state)
        elif phase == BattlePhase.GAME_OVER:
            if input_state.btn_ok or input_state.mouse_clicked:
                return SceneTransition.to(SceneId.TITLE)
        else:
            if self.visual.is_waiting_for_advance(phase) and (input_state.btn_ok or input_state.mouse_clicked):
                self._advance_phase()

        return SceneTransition.stay()

    def _handle_input_phase(self, input_state):
        items = self._build_command_menu_items()
        if not items:
            return

        selectable_mask = to_selectable_mask(items)

        if input_state.mouse_clicked:
            self._handle_mouse_input(items, selectable_mask, input_state)
            return

        self.selected_button_index = resolve_command_menu_navigation(
            self.selected_button_index, input_state, selectable_mask
        )

        if input_state.btn_ok:
            self._confirm_selection(items)

    def _handle_mouse_input(self, items, selectable_mask, input_state):
        if self.screen is None:
            return

        screen_size = self.screen.get_size()
        new_index, confirmed = hit_test_command_menu(
            screen_size,
            (input_state.mouse_x, input_state.mouse_y),
            len(items),
            self.selected_button_index,
        )
        if 0 <= new_index < len(selectable_mask) and selectable_mask[new_index]:
            self.selected_button_index = new_index
        if confirmed:
            self._confirm_selection(items)

    def _build_command_menu_items(self):
        actor = self.manager.current_actor
        if not actor:
            return []
        return build_command_menu_items(actor, self.manager.ctx.preview_targets, self.manager.robots)

    def _confirm_selection(self, items):
        if not (0 <= self.selected_button_index < len(items)):
            return
        item = items[self.selected_button_index]
        if item.selectable:
            self.manager.select_command_slot(item.slot_type)

    def _advance_phase(self):
        if self.visual.is_busy():
            return

        phase = self.manager.phase
        if phase in (BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT):
            self._handle_cutin_advance()
        elif phase == BattlePhase.ATTACK_DECLARATION:
            self._advance_attack_declaration()
        else:
            self.manager.advance_phase()

    def _advance_attack_declaration(self):
        actor = self.manager.current_actor
        part = actor.current_part if actor else None
        if actor and part and part.is_implemented and part.presentation == SkillPresentation.CUTIN:
            report = self.manager.ctx.current_report
            if report and report.result:
                self.visual.start_cutin(part, report)
        self.manager.advance_phase()

    def _handle_cutin_advance(self):
        if not self.visual.cutin_director:
            self._complete_action_execution()
            return

        for event in self.visual.advance_cutin():
            if event == CutinEvent.ANIMATION_FINISHED:
                self._apply_and_stage_damage()
                self.manager.change_phase(BattlePhase.CUTIN_RESULT)
            elif event == CutinEvent.PIERCE_ADVANCED:
                self.manager.ctx.set_log(["貫通ダメージ！"])
                report = self.manager.ctx.current_report
                if report and report.target:
                    self.visual.advance_damage_step(report.target)
            elif event == CutinEvent.COMPLETED:
                self._complete_action_execution()

    def _apply_and_stage_damage(self):
        self.manager.apply_execution_result()
        report = self.manager.ctx.current_report
        if report:
            self.visual.stage_damage(report)
            if report.result:
                self.visual.update_cutin_result(report.result)

    def _complete_action_execution(self):
        self.visual.sync_all_targets()
        self.visual.clear_cutin()
        self.visual.clear_radar()
        self.manager.complete_execution()

    def update(self, dt: float):
        # 1. 演出タイマー・アニメーションの更新
        self.visual.update(dt)

        # 2. フェーズ切り替えの検知と演出トリガー
        current_phase = self.manager.phase
        if current_phase != self._last_phase:
            self._on_phase_changed(current_phase)
            self._last_phase = current_phase

        # 3. カットイン実行中のアニメーション進行
        if current_phase == BattlePhase.CUTIN:
            events = self.visual.update_cutin(dt)
            if events:
                for event in events:
                    if event == CutinEvent.ANIMATION_FINISHED:
                        self._apply_and_stage_damage()
                        self.manager.change_phase(BattlePhase.CUTIN_RESULT)
            elif not self.visual.cutin_director:
                self._apply_and_stage_damage()
                self.manager.change_phase(BattlePhase.CUTIN_RESULT)

        # 4. タイマーによる自動遷移フェーズ
        elif current_phase in (BattlePhase.OPENING_POPUP, BattlePhase.TARGET_INDICATION):
            if self.visual.is_timer_expired():
                config = PHASE_CONFIGS.get(current_phase)
                next_phase = config.next_phase if config else None
                if next_phase:
                    if current_phase == BattlePhase.OPENING_POPUP:
                        self.manager.advance_phase()
                    else:
                        self.manager.change_phase(next_phase)

        # 5. 純粋ロジック（ATB・割り込みなど）の更新
        # （HPアニメーション中などは割り込み・新規ターン発火を停止）
        if not self.visual.is_hp_animating():
            self.manager.update(dt)

    def _on_phase_changed(self, new_phase: BattlePhase):
        config = PHASE_CONFIGS.get(new_phase)
        self.visual.start_phase_timer(config.duration if config else 0.0)

        if new_phase == BattlePhase.TARGET_INDICATION:
            actor = self.manager.current_actor
            report = self.manager.ctx.current_report
            target = report.target if report else None
            if actor and target:
                actor_idx = self._find_robot_index(actor)
                target_idx = self._find_robot_index(target)
                if actor_idx is not None and target_idx is not None:
                    self.visual.start_radar(actor_idx, target_idx)

    def _find_robot_index(self, robot) -> Optional[int]:
        for idx, candidate in enumerate(self.manager.robots):
            if candidate is robot:
                return idx
        return None

    def render(self):
        if self.renderer is not None:
            model = self.view_builder.build(self.selected_button_index)
            self.renderer.render(model)
