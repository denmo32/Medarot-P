"""バトル画面のシーン（型付き遷移・集約入力駆動・決定論的RNG・Directorによる完全調停）"""
import random
from typing import Optional
from core.scene_manager import Scene, SceneTransition
from core.constants import SceneId
from features.battle.factory import BattleFactory
from features.battle.input.command_menu_navigation import resolve_command_menu_navigation
from features.battle.manager import BattleManager
from features.battle.presentation.command_menu_builder import (
    build_command_menu_items,
    to_selectable_mask,
)
from features.battle.presentation.view_builder import BattleViewBuilder
from features.battle.staging.director import BattleDirector
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

        # 1. 純粋シミュレーション
        self.manager = BattleManager(player_setups, enemy_setups, ctx.data_manager, seed=self.seed)
        # 2. 視覚演出状態
        self.visual = VisualCoordinator(self.manager.ctx.robots)
        # 3. yield スケジューラ（ディレクター）
        self.director = BattleDirector(self.manager, self.visual)
        # 4. 表示モデル構築
        self.view_builder = BattleViewBuilder(self.manager.ctx, self.visual, self.director)
        # 5. レンダラー
        self.renderer = BattleRenderer(self.screen) if self.screen is not None else None

        self.selected_button_index = 0

    def handle_input(self, input_state) -> SceneTransition:
        if input_state.btn_menu:
            return SceneTransition.to(SceneId.TITLE)

        if self.director.is_game_over:
            if input_state.btn_ok or input_state.mouse_clicked:
                return SceneTransition.to(SceneId.TITLE)
            return SceneTransition.stay()

        # プレイヤーコマンド選択中の専用入力処理
        input_await = self.director.current_player_input_await
        if input_await is not None:
            self._handle_command_input(input_state, input_await)
            return SceneTransition.stay()

        # 通常の待機状態（確認・スキップ等）は Director に委譲
        self.director.handle_input(input_state)
        return SceneTransition.stay()

    def _handle_command_input(self, input_state, input_await):
        items = build_command_menu_items(
            input_await.actor, input_await.preview_targets, self.manager.robots
        )
        if not items:
            return

        selectable_mask = to_selectable_mask(items)

        if input_state.mouse_clicked and self.screen is not None:
            screen_size = self.screen.get_size()
            new_index, confirmed = hit_test_command_menu(
                screen_size,
                (input_state.mouse_x, input_state.mouse_y),
                len(items),
                self.selected_button_index,
            )
            if 0 <= new_index < len(selectable_mask) and selectable_mask[new_index]:
                self.selected_button_index = new_index
            if confirmed and items[self.selected_button_index].selectable:
                input_await.submit(items[self.selected_button_index].part_type)
                self.director.advance()
            return

        self.selected_button_index = resolve_command_menu_navigation(
            self.selected_button_index, input_state, selectable_mask
        )

        if input_state.btn_ok and items[self.selected_button_index].selectable:
            input_await.submit(items[self.selected_button_index].part_type)
            self.director.advance()

    def update(self, dt: float):
        self.visual.update(dt)
        self.director.tick(dt)

    def render(self):
        if self.renderer is not None:
            model = self.view_builder.build(self.selected_button_index)
            self.renderer.render(model)