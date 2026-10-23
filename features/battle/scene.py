"""バトル画面のシーン（型付き遷移・集約入力駆動・決定論的RNG・Directorによる完全調停）"""
import random
from typing import Optional
from core.scene_manager import Scene, SceneTransition
from core.constants import SceneId
from domain.constants import COMMAND_MENU_PART_ORDER
from features.battle.factory import BattleFactory
from features.battle.manager import BattleManager
from features.battle.presentation.view_builder import BattleViewBuilder
from features.battle.staging.director import BattleDirector
from features.battle.staging.visual_coordinator import VisualCoordinator
from features.battle.ui.layout import hit_test_command_menu
from features.battle.ui.renderer import BattleRenderer


class BattleScene(Scene):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.seed = None
        self.manager = None
        self.visual = None
        self.director = None
        self.view_builder = None
        self.renderer = BattleRenderer(self.screen) if self.screen is not None else None

    def on_enter(self, seed: Optional[int] = None, **payload):
        """SceneManager.switch_to から渡されたシード値を確実に受領・初期化"""
        self.seed = seed if seed is not None else random.randrange(2**32)
        battle_rng = random.Random(self.seed)

        player_setups = BattleFactory.get_player_setups(self.ctx.save_manager)
        enemy_setups = BattleFactory.get_enemy_setups(self.ctx.data_manager, rng=battle_rng)

        # 1. 純粋シミュレーション
        self.manager = BattleManager(player_setups, enemy_setups, self.ctx.data_manager, seed=self.seed)
        # 2. 視覚演出状態
        self.visual = VisualCoordinator(self.manager.ctx.robots)
        # 3. yield スケジューラ（ディレクター）
        self.director = BattleDirector(self.manager, self.visual)
        # 4. 表示モデル構築
        self.view_builder = BattleViewBuilder(self.manager.ctx, self.visual, self.director)

    def handle_input(self, input_state) -> SceneTransition:
        if input_state.btn_menu:
            return SceneTransition.to(SceneId.TITLE)

        if self.director is None:
            return SceneTransition.stay()

        if self.director.is_game_over:
            if input_state.btn_ok or input_state.mouse_clicked:
                return SceneTransition.to(SceneId.TITLE)
            return SceneTransition.stay()

        # マウス操作のみ Scene（画面解像度を持つ層）で判定し、Await に委譲
        input_await = self.director.current_player_input_await
        if input_await and input_state.mouse_clicked and self.screen is not None:
            screen_size = self.screen.get_size()
            new_index, confirmed = hit_test_command_menu(
                screen_size,
                (input_state.mouse_x, input_state.mouse_y),
                len(COMMAND_MENU_PART_ORDER),
                input_await.selected_index,
            )
            if input_await.try_mouse_select(new_index, confirmed):
                self.director.advance()
            return SceneTransition.stay()

        # キーボード・パッド入力は原則通り Director に完全一元委譲
        self.director.handle_input(input_state)
        return SceneTransition.stay()

    def update(self, dt: float):
        if self.visual is not None:
            self.visual.update(dt)
        if self.director is not None:
            self.director.tick(dt)

    def render(self):
        if self.renderer is None or self.view_builder is None or self.director is None:
            return
        
        # Await 側の選択インデックスを安全に参照
        selected_index = 0
        if input_await := self.director.current_player_input_await:
            selected_index = input_await.selected_index

        model = self.view_builder.build(selected_index)
        self.renderer.render(model)