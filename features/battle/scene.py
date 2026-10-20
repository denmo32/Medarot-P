"""バトル画面のシーン（型付き遷移・集約入力駆動・決定論的RNG・演出とロジックの調停）"""
import random
from typing import Optional, Sequence
from core.scene_manager import Scene, SceneTransition
from core.constants import SceneId
from features.battle.constants import BattlePhase
from features.battle.factory import BattleFactory
from features.battle.flow import (
    AdvanceTrigger,
    BattleFlow,
    FlowEvent,
    PhaseChangeEvent,
    PierceStepEvent,
    ActionCompletedEvent,
)
from features.battle.presentation.command_menu_builder import (
    build_command_menu_items,
    to_selectable_mask,
)
from features.battle.presentation.view_builder import BattleViewBuilder
from features.battle.input.command_menu_navigation import resolve_command_menu_navigation
from features.battle.manager import BattleManager
from features.battle.staging.cutin_director import CutinEvent
from features.battle.staging.visual_coordinator import VisualCoordinator
from features.battle.ui.layout import hit_test_command_menu
from features.battle.ui.renderer import BattleRenderer


class BattleScene(Scene):
    def __init__(self, ctx, seed: Optional[int] = None):
        super().__init__(ctx)
        self.seed = seed if seed is not None else random.randrange(2**32)
        battle_rng = random.Random(self.seed)

        player_setups = BattleFactory.get_player_setups(ctx.save_manager)
        enemy_setups = BattleFactory.get_enemy_setups(ctx.data_manager, rng=battle_rng)

        # 1. 純粋シミュレーション (BattleManager)
        self.manager = BattleManager(player_setups, enemy_setups, ctx.data_manager, seed=self.seed)
        # 2. 進行・状態機械 (BattleFlow)
        self.flow = BattleFlow(self.manager)
        # 3. 演出進行 (VisualCoordinator)
        self.visual = VisualCoordinator(self.manager.ctx.robots)
        # 4. 表示モデル構築 (ViewBuilder)
        self.view_builder = BattleViewBuilder(self.manager.ctx, self.visual, self.flow)
        # 5. レンダラー (Renderer)
        self.renderer = BattleRenderer(self.screen) if self.screen is not None else None

        self.selected_button_index = 0

    def handle_input(self, input_state) -> SceneTransition:
        if input_state.btn_menu:
            return SceneTransition.to(SceneId.TITLE)

        phase = self.flow.phase

        if phase == BattlePhase.INPUT:
            self._handle_input_phase(input_state)
        elif phase == BattlePhase.GAME_OVER:
            if input_state.btn_ok or input_state.mouse_clicked:
                return SceneTransition.to(SceneId.TITLE)
        else:
            if (input_state.btn_ok or input_state.mouse_clicked) and not self.visual.is_hp_animating():
                events = self.flow.advance(AdvanceTrigger.USER_CONFIRM)
                self._dispatch_events(events)

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
            events = self.flow.submit_player_command(item.slot_type)
            self._dispatch_events(events)

    def update(self, dt: float):
        # 1. 演出（HPアニメーション・レーダーなど）の進行
        self.visual.update(dt)

        # 2. カットイン演出の物理終了検知
        if self.flow.phase == BattlePhase.CUTIN:
            cutin_events = self.visual.update_cutin(dt)
            if CutinEvent.ANIMATION_FINISHED in cutin_events or not self.visual.cutin_director:
                events = self.flow.advance(AdvanceTrigger.ANIMATION_END)
                self._dispatch_events(events)

        # 3. 進行・シミュレーションの更新（HPアニメ中は停止）
        if not self.visual.is_hp_animating():
            flow_events = self.flow.update(dt)
            self._dispatch_events(flow_events)

    def _dispatch_events(self, events: Sequence[FlowEvent]):
        """Flow から発行されたイベントを受け取り、演出コンポーネントを駆動する"""
        for event in events:
            if isinstance(event, PhaseChangeEvent):
                self._on_phase_changed(event.new_phase)
            elif isinstance(event, PierceStepEvent):
                self.visual.advance_damage_step(event.target)
            elif isinstance(event, ActionCompletedEvent):
                self._finalize_action_visuals()

    def _on_phase_changed(self, new_phase: BattlePhase):
        """フェーズ切り替え時に対応する演出を起動する"""
        if new_phase == BattlePhase.TARGET_INDICATION:
            self._start_radar_visuals()
        elif new_phase == BattlePhase.CUTIN:
            self._start_cutin_visuals()
        elif new_phase == BattlePhase.CUTIN_RESULT:
            self._stage_damage_visuals()

    def _start_radar_visuals(self):
        actor = self.manager.current_actor
        report = self.manager.ctx.current_report
        target = report.target if report else None
        if actor and target:
            actor_idx = self._find_robot_index(actor)
            target_idx = self._find_robot_index(target)
            if actor_idx is not None and target_idx is not None:
                self.visual.start_radar(actor_idx, target_idx)

    def _start_cutin_visuals(self):
        actor = self.manager.current_actor
        part = actor.current_part if actor else None
        report = self.manager.ctx.current_report
        if part and report and report.result:
            self.visual.start_cutin(part, report)

    def _stage_damage_visuals(self):
        report = self.manager.ctx.current_report
        if report:
            self.visual.stage_damage(report)
            if report.result:
                self.visual.update_cutin_result(report.result)

    def _finalize_action_visuals(self):
        self.visual.sync_all_targets()
        self.visual.clear_cutin()
        self.visual.clear_radar()

    def _find_robot_index(self, robot) -> Optional[int]:
        for idx, candidate in enumerate(self.manager.robots):
            if candidate is robot:
                return idx
        return None

    def render(self):
        if self.renderer is not None:
            model = self.view_builder.build(self.selected_button_index)
            self.renderer.render(model)