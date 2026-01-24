"""タイトル画面の実装"""

import pygame
from core.ecs import World
from input.event_manager import EventManager
from config import COLORS, FONT_NAMES, GAME_PARAMS

class TitleScene:
    """タイトル画面のクラス"""

    def __init__(self, screen):
        self.screen = screen
        
        # ECSとイベントマネージャのセットアップ（入力統一のため）
        self.world = World()
        self.event_manager = EventManager(self.world)
        
        # UIリソース
        self.font = pygame.font.SysFont(FONT_NAMES, 48)
        self.button_font = pygame.font.SysFont(FONT_NAMES, 32)
        
        # 状態
        self.selected_index = 0
        self.title_text = "Medarot-P"
        
        # ボタン定義
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
        # 背景
        self.screen.fill(COLORS['BACKGROUND'])

        # タイトル
        title_surface = self.font.render(self.title_text, True, COLORS['TEXT'])
        title_rect = title_surface.get_rect(center=(GAME_PARAMS['SCREEN_WIDTH'] // 2, 150))
        self.screen.blit(title_surface, title_rect)

        # ボタン
        for i, button in enumerate(self.buttons):
            self._draw_button(button, i == self.selected_index)

        pygame.display.flip()

    def _draw_button(self, button, is_selected):
        # 背景
        pygame.draw.rect(self.screen, COLORS['BUTTON_BG'], button['rect'])
        
        # 枠線（選択時は黄色で太く）
        border_color = (255, 255, 0) if is_selected else COLORS['BUTTON_BORDER']
        border_width = 3 if is_selected else 2
        pygame.draw.rect(self.screen, border_color, button['rect'], border_width)

        # テキスト
        text_surface = self.button_font.render(button['text'], True, COLORS['TEXT'])
        text_rect = text_surface.get_rect(center=button['rect'].center)
        self.screen.blit(text_surface, text_rect)