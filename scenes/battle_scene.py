"""バトル画面のシーンラッパー"""

import pygame
from battle.manager import BattleSystem
from input.event_manager import EventManager

class BattleScene:
    """バトル画面のクラス"""

    def __init__(self, screen):
        self.screen = screen
        self.battle_system = BattleSystem(screen)
        self.event_manager = EventManager(self.battle_system.world)
        self.running = True

    def handle_events(self):
        """イベント処理"""
        # EventManagerを通じてバトルシステムのイベントを処理
        running = self.event_manager.handle_events()
        if not running:
            return 'quit'
        
        # 追加のイベント処理（ESCキーでタイトルに戻る）
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            return 'title'  # ESCキーでタイトルに戻る
            
        return None

    def update(self, dt):
        """更新処理"""
        # バトルシステムの更新
        self.battle_system.update(dt)

    def render(self):
        """描画処理はバトルシステム内部で行われる"""
        pass
