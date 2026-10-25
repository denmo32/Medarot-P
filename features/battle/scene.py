# features/battle/scene.py
"""バトル画面のシーン（型付き遷移・集約入力駆動・決定論的RNG・Directorによる完全調停）"""
import random
from typing import Optional
from core.scene_manager import Scene, SceneTransition
from core.constants import SceneId
from features.battle.input.command_menu_controller import CommandMenuController
from features.battle.simulation.factory import BattleFactory
from features.battle.simulation.manager import BattleManager
from features.battle.staging.directives import AwaitPlayerInput
from features.battle.staging.director import BattleDirector
from features.battle.ui.renderer import BattleRenderer


class BattleScene(Scene):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.seed = None
        self.manager: Optional[BattleManager] = None
        self.director: Optional[BattleDirector] = None
        self.renderer = BattleRenderer(self.screen) if self.screen is not None else None
        self.menu_controller = CommandMenuController()
        self._last_player_input_await: Optional[AwaitPlayerInput] = None

    def on_enter(self, seed: Optional[int] = None, **payload):
        self.seed = seed if seed is not None else random.randrange(2**32)
        battle_rng = random.Random(self.seed)

        player_setups = BattleFactory.get_player_setups(self.ctx.save_manager)
        enemy_setups = BattleFactory.get_enemy_setups(self.ctx.data_manager, rng=battle_rng)

        # 1. バトルシミュレーション
        self.manager = BattleManager(player_setups, enemy_setups, self.ctx.data_manager, seed=self.seed)
        self.director = BattleDirector(self.manager)
        self.menu_controller.reset()
        self._last_player_input_await = None

    def handle_input(self, input_state) -> SceneTransition:
        if input_state.btn_menu:
            return SceneTransition.to(SceneId.TITLE)

        if self.director is None:
            return SceneTransition.stay()

        if self.director.is_game_over:
            if input_state.btn_ok or input_state.mouse_clicked:
                return SceneTransition.to(SceneId.TITLE)
            return SceneTransition.stay()

        player_input_await = self.director.current_player_input_await
        if player_input_await is not None:
            if player_input_await is not self._last_player_input_await:
                self._last_player_input_await = player_input_await
                self.menu_controller.reset()

            screen_size = self.screen.get_size() if self.screen is not None else None
            result = self.menu_controller.resolve_input(
                input_state=input_state,
                menu_items=player_input_await.menu_items,
                screen_size=screen_size,
            )

            if result.confirmed:
                self.director.submit_player_command(result.chosen_part)

            return SceneTransition.stay()

        self._last_player_input_await = None

        if input_state.btn_ok or input_state.mouse_clicked:
            self.director.confirm_or_advance()

        return SceneTransition.stay()

    def update(self, dt: float):
        if self.director is not None:
            self.director.tick(dt)

    def render(self):
        if self.renderer is not None and self.director is not None:
            self.renderer.render(
                self.director,
                selected_command_index=self.menu_controller.selected_index,
            )