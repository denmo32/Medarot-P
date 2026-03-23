"""バトル画面のシーンラッパー"""

import pygame
from battle.battle_orchestrator import BattleEngine
from input.event_manager import EventManager
from data.game_data_manager import GameDataManager
from data.save_data_manager import SaveDataManager
from ui.config import UI_PARAMS
from ui.battle.system import BattleRenderSystem
from ui.battle.visual_systems import HealthAnimationSystem

class BattleScene:
    """バトル画面のクラス"""

    def __init__(self, screen, data_manager: GameDataManager, save_manager: SaveDataManager):
        self.screen = screen
        # ロジックエンジンの初期化（UIパラメータを注入）
        self.battle_engine = BattleEngine(data_manager, save_manager, UI_PARAMS)
        self.world = self.battle_engine.world
        self.view_model = self.battle_engine.view_model

        self.event_manager = EventManager(self.world)

        # UI系システムの初期化
        self.health_animation_system = HealthAnimationSystem(self.world)
        self.battle_render_system = BattleRenderSystem(self.world, screen, self.view_model)

        self.running = True

    def handle_events(self):
        """イベント処理"""
        # EventManagerを通じてバトルシステムのイベントを処理
        running = self.event_manager.handle_events()
        if not running:
            return 'quit'

        # InputComponentを取得して共通操作（中断）を確認
        input_comp = self.world.entities[self.event_manager.input_entity_id]['input']

        if input_comp.btn_menu: # ESCキーなど
            return 'title'

        return None

    def update(self, dt):
        """更新処理"""
        # ロジックの更新
        self.battle_engine.update(dt)
        # 視覚的な演出（HPバーのアニメーション等）の更新
        self.health_animation_system.update(dt)

    def render(self):
        """描画処理"""
        # レンダリングシステムの実行
        self.battle_render_system.update(0)