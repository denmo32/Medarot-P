"""タイトル画面の実装"""

import pygame
from core.ecs import World
from input.event_manager import EventManager
from ui.title_renderer import TitleRenderer

class TitleScene:
    """タイトル画面のクラス (Manager/Presenter)"""

    def __init__(self, screen):
        # レンダラーの初期化 (View)
        self.renderer = TitleRenderer(screen)
        
        # ECSとイベントマネージャのセットアップ
        self.world = World()
        self.event_manager = EventManager(self.world)
        
        # 状態
        self.selected_index = 0
        
        # ボタン定義 (相対座標で定義)
        # cx: 中央オフセットなし(0.5), cy: Y位置(0.5が中央)
        self.buttons = [
            {
                'text': 'バトル開始',
                'action': 'battle',
                'layout': {'cx': 0.5, 'cy': 0.55, 'w_ratio': 0.25, 'h_ratio': 0.1}
            },
            {
                'text': 'カスタマイズ',
                'action': 'customize',
                'layout': {'cx': 0.5, 'cy': 0.68, 'w_ratio': 0.25, 'h_ratio': 0.1}
            }
        ]

    def handle_events(self):
        """イベント処理"""
        # EventManagerを通じて入力を更新
        if not self.event_manager.handle_events():
            return 'quit'
            
        input_comp = self.world.entities[self.event_manager.input_entity_id]['input']
        
        # 論理入力による操作
        if input_comp.btn_up:
            self.selected_index = (self.selected_index - 1) % len(self.buttons)
        elif input_comp.btn_down:
            self.selected_index = (self.selected_index + 1) % len(self.buttons)
        elif input_comp.btn_ok:
            return self.buttons[self.selected_index]['action']
        elif input_comp.btn_menu: # ESC
            return 'quit'
            
        # マウス操作 (当たり判定のために現在の画面サイズでRectを計算する必要がある)
        if input_comp.mouse_clicked or True: # ホバーも判定するため常に計算
            sw, sh = self.renderer.screen.get_width(), self.renderer.screen.get_height()
            
            for i, button in enumerate(self.buttons):
                layout = button['layout']
                w, h = sw * layout['w_ratio'], sh * layout['h_ratio']
                x = sw * layout['cx'] - w / 2
                y = sh * layout['cy'] - h / 2
                rect = pygame.Rect(x, y, w, h)
                
                if rect.collidepoint(input_comp.mouse_x, input_comp.mouse_y):
                    self.selected_index = i
                    if input_comp.mouse_clicked:
                        return button['action']
        
        return None

    def update(self, dt):
        """更新処理"""
        pass

    def render(self):
        """描画処理"""
        ui_data = {
            'buttons': self.buttons,
            'selected_index': self.selected_index
        }
        self.renderer.render(ui_data)