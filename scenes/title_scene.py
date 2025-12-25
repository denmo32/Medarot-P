"""タイトル画面の実装"""

import pygame
from config import COLORS, FONT_NAMES, GAME_PARAMS

class TitleScene:
    """タイトル画面のクラス"""

    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont(FONT_NAMES, 48)
        self.button_font = pygame.font.SysFont(FONT_NAMES, 32)
        self.title_text = "Medarot-P"
        self.running = True

        # ボタンの設定
        button_width = 200
        button_height = 60
        button_padding = 20
        screen_center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
        start_y = 300

        self.battle_button = {
            'rect': pygame.Rect(screen_center_x - button_width // 2, start_y, button_width, button_height),
            'text': 'バトル開始',
            'action': 'battle'
        }

        self.customize_button = {
            'rect': pygame.Rect(screen_center_x - button_width // 2, start_y + button_height + button_padding, button_width, button_height),
            'text': 'カスタマイズ',
            'action': 'customize'
        }

        self.buttons = [self.battle_button, self.customize_button]

    def handle_events(self):
        """イベント処理"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'quit'
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左クリック
                    mouse_pos = pygame.mouse.get_pos()
                    for button in self.buttons:
                        if button['rect'].collidepoint(mouse_pos):
                            return button['action']
        return None

    def update(self, dt):
        """更新処理"""
        pass

    def render(self):
        """描画処理"""
        # 背景の描画
        self.screen.fill(COLORS['BACKGROUND'])

        # タイトルの描画
        title_surface = self.font.render(self.title_text, True, COLORS['TEXT'])
        title_rect = title_surface.get_rect(center=(GAME_PARAMS['SCREEN_WIDTH'] // 2, 150))
        self.screen.blit(title_surface, title_rect)

        # ボタンの描画
        for button in self.buttons:
            # ボタン背景
            pygame.draw.rect(self.screen, COLORS['BUTTON_BG'], button['rect'])
            pygame.draw.rect(self.screen, COLORS['BUTTON_BORDER'], button['rect'], 2)

            # ボタンテキスト
            text_surface = self.button_font.render(button['text'], True, COLORS['TEXT'])
            text_rect = text_surface.get_rect(center=button['rect'].center)
            self.screen.blit(text_surface, text_rect)

        pygame.display.flip()
