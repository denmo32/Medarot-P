# features/battle/scene.py
"""バトル画面のシーン（型付き遷移・集約入力駆動・決定論的RNG・Directorによる完全調停）"""
import random
from typing import Optional
from core.scene_manager import Scene, SceneTransition
from core.constants import SceneId
from features.battle.simulation.factory import BattleFactory
from features.battle.simulation.manager import BattleManager
from features.battle.staging.director import BattleDirector
from features.battle.ui.renderer import BattleRenderer


class BattleScene(Scene):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.seed = None
        self.manager: Optional[BattleManager] = None
        self.director: Optional[BattleDirector] = None
        self.renderer = BattleRenderer(self.screen) if self.screen is not None else None

    def on_enter(self, seed: Optional[int] = None, **payload):
        self.seed = seed if seed is not None else random.randrange(2**32)
        battle_rng = random.Random(self.seed)

        player_setups = BattleFactory.get_player_setups(self.ctx.save_manager)
        enemy_setups = BattleFactory.get_enemy_setups(self.ctx.data_manager, rng=battle_rng)

        # 1. バトルシミュレーション
        self.manager = BattleManager(player_setups, enemy_setups, self.ctx.data_manager, seed=self.seed)
        # 2. 進行スケジューラ（ディレクター）
        self.director = BattleDirector(self.manager)

    def handle_input(self, input_state) -> SceneTransition:
        if input_state.btn_menu:
            return SceneTransition.to(SceneId.TITLE)

        if self.director is None:
            return SceneTransition.stay()

        if self.director.is_game_over:
            if input_state.btn_ok or input_state.mouse_clicked:
                return SceneTransition.to(SceneId.TITLE)
            return SceneTransition.stay()

        screen_size = self.screen.get_size() if self.screen is not None else None
        self.director.handle_input(input_state, screen_size)
        return SceneTransition.stay()

    def update(self, dt: float):
        if self.director is not None:
            self.director.tick(dt)

    def render(self):
        if self.renderer is not None and self.director is not None:
            self.renderer.render(self.director)