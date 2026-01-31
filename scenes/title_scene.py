"""タイトル画面の実装"""

import pygame
from core.ecs import World
from input.event_manager import EventManager
from config import GAME_PARAMS
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
        
        # ボタン定義 (Model/Layout logic)
        button_width = 200
        button_height = 60
        button_padding = 20
        screen_center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
        start_y = 300

        self.buttons = [
            {
                'rect': pygame.Rect(screen_center_x - button_width // 2, start_y, button_width, button_height),
                'text': 'バトル開始',
                'action': 'battle'
            },
            {
                'rect': pygame.Rect(screen_center_x - button_width // 2, start_y + button_height + button_padding, button_width, button_height),
                'text': 'カスタマイズ',
                'action': 'customize'
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
            
        # マウス操作
        if input_comp.mouse_clicked:
            for i, button in enumerate(self.buttons):
                if button['rect'].collidepoint(input_comp.mouse_x, input_comp.mouse_y):
                    return button['action']
        
        # マウスホバー
        for i, button in enumerate(self.buttons):
            if button['rect'].collidepoint(input_comp.mouse_x, input_comp.mouse_y):
                self.selected_index = i
        
        return None

    def update(self, dt):
        """更新処理"""
        pass

    def render(self):
        """描画処理"""
        # レンダラーに現在の状態（DTO）を渡して描画させる
        ui_data = {
            'buttons': self.buttons,
            'selected_index': self.selected_index
        }
        self.renderer.render(ui_data)