"""バトル画面のシーン（型付き遷移・集約入力駆動・決定論的RNG・ヘッドレス両対応）"""
import random
from typing import Optional
from core.scene_manager import Scene, SceneTransition
from domain.constants import SceneId
from features.battle.constants import BattlePhase
from features.battle.factory import BattleFactory
from features.battle.input.command_menu_model import (
    build_command_menu_items,
    to_selectable_mask,
)
from features.battle.input.command_menu_navigation import resolve_command_menu_navigation
from features.battle.manager import BattleManager
from features.battle.presentation.view_builder import BattleViewBuilder
from ui.base.interaction import handle_menu_mouse
from ui.battle.layout import calculate_command_menu_rects
from ui.battle.renderer import BattleRenderer


class BattleScene(Scene):
    def __init__(self, ctx, seed: Optional[int] = None):
        super().__init__(ctx)
        self.seed = seed if seed is not None else random.randrange(2**32)
        battle_rng = random.Random(self.seed)

        player_setups = BattleFactory.get_player_setups(ctx.save_manager)
        enemy_setups = BattleFactory.get_enemy_setups(ctx.data_manager, rng=battle_rng)

        self.manager = BattleManager(player_setups, enemy_setups, ctx.data_manager, seed=self.seed)
        self.view_builder = BattleViewBuilder(self.manager)
        # screen が渡されている場合のみ Renderer を生成（ヘッドレステスト環境に対応）
        self.renderer = BattleRenderer(self.screen) if self.screen is not None else None
        self.selected_button_index = 0

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
            if self.manager.is_waiting_for_advance() and (input_state.btn_ok or input_state.mouse_clicked):
                self.manager.advance_phase()

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
        sw, sh = self.screen.get_size()
        layouts = calculate_command_menu_rects(len(items), (sw, sh))
        new_index, confirmed = handle_menu_mouse(
            (input_state.mouse_x, input_state.mouse_y), True, layouts, self.selected_button_index
        )
        if 0 <= new_index < len(selectable_mask) and selectable_mask[new_index]:
            self.selected_button_index = new_index
        if confirmed:
            self._confirm_selection(items)

    def _build_command_menu_items(self):
        actor = self.manager.current_actor
        if not actor:
            return []
        return build_command_menu_items(actor, self.manager.get_command_menu_preview_targets(), self.manager.robots)

    def _confirm_selection(self, items):
        if not (0 <= self.selected_button_index < len(items)):
            return
        item = items[self.selected_button_index]
        if item.selectable:
            self.manager.select_command_slot(item.slot_type)

    def update(self, dt: float):
        self.manager.update(dt)

    def render(self):
        if self.renderer is not None:
            self.renderer.render(self.view_builder.build(self.selected_button_index))