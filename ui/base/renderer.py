"""
全シーン共通の描画基盤
ECSの状態を一切知らず、受け取った値の描画のみを行う低レベルなラッパー。
"""

import pygame
from ui.config import COLORS, FONT_NAMES, ACTION_BUTTON_FONT_NAME, SCREEN_HEIGHT
from core.utils import resource_path

class BaseRenderer:
    def __init__(self, screen):
        self.screen = screen
        self._init_fonts()

    @property
    def ui_scale(self) -> float:
        """現在の画面高さに基づくスケーリング係数"""
        return self.screen.get_height() / SCREEN_HEIGHT

    def scaled(self, value: float) -> int:
        """基準解像度(高さ)に基づく値を現在の解像度にスケーリングして整数で返す"""
        return int(value * self.ui_scale)

    def _init_fonts(self):
        """フォントの初期化。画面サイズに応じたスケーリングはここで行う"""
        font_path = resource_path(FONT_NAMES[0]) if FONT_NAMES else resource_path('freesansbold.ttf')
        button_font_path = resource_path(ACTION_BUTTON_FONT_NAME)
        
        # フォントサイズ設定 (初期化時のスケールで固定)
        scale = self.ui_scale

        self.fonts = {
            'small': pygame.font.Font(font_path, int(14 * scale)),
            'normal': pygame.font.Font(font_path, int(20 * scale)),
            'medium': pygame.font.Font(font_path, int(24 * scale)),
            'large': pygame.font.Font(font_path, int(32 * scale)),
            'notice': pygame.font.Font(font_path, int(36 * scale)),
            'action_button': pygame.font.Font(button_font_path, int(24 * scale)),
            'action_button_focus': pygame.font.Font(button_font_path, int(28 * scale))
        }

    def clear(self):
        self.screen.fill(COLORS['BACKGROUND'])

    def present(self):
        pygame.display.flip()

    # --- 座標変換ユーティリティ ---
    
    def get_screen_size(self):
        return self.screen.get_width(), self.screen.get_height()

    def to_px(self, rx: float, ry: float) -> tuple[int, int]:
        """相対座標(0.0~1.0)を絶対座標(px)に変換"""
        w, h = self.get_screen_size()
        return int(rx * w), int(ry * h)

    def scale_x(self, ratio: float) -> int:
        return int(ratio * self.screen.get_width())

    def scale_y(self, ratio: float) -> int:
        return int(ratio * self.screen.get_height())
    
    # --- 描画プリミティブ ---

    def draw_box(self, rect, bg_color, border_color=None, border_width=2):
        """背景と枠線を持つ矩形を描画"""
        pygame.draw.rect(self.screen, bg_color, rect)
        if border_color:
            pygame.draw.rect(self.screen, border_color, rect, border_width)

    def draw_text(self, text, pos, color=COLORS['TEXT'], font_type='normal', align='left'):
        """テキストを描画"""
        surf = self.fonts[font_type].render(str(text), True, color)
        rect = surf.get_rect()
        if align == 'left':
            rect.topleft = pos
        elif align == 'center':
            rect.center = pos
        elif align == 'right':
            rect.topright = pos
        self.screen.blit(surf, rect)

    def draw_text_with_outline(self, text, x, y, color, font_type='normal', align='left', outline_color=(0, 0, 0)):
        """縁取り付きテキストを描画"""
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            self.draw_text(text, (x + ox, y + oy), outline_color, font_type, align)
        self.draw_text(text, (x, y), color, font_type, align)

    def draw_bar(self, rect, ratio, bg_color, fg_color, border_color=(150, 150, 150)):
        """プログレスバーを描画"""
        # 背景
        pygame.draw.rect(self.screen, bg_color, rect)
        # 中身
        fill_w = int(rect[2] * max(0, min(1.0, ratio)))
        if fill_w > 0:
            pygame.draw.rect(self.screen, fg_color, (rect[0], rect[1], fill_w, rect[3]))
        # 枠線
        if border_color:
            pygame.draw.rect(self.screen, border_color, rect, 1)

    def draw_triangle(self, pos, angle, size, color):
        """指定した角度の三角形を描画"""
        import math
        cx, cy = pos
        # 先端
        p1 = (cx + math.cos(angle) * size, cy + math.sin(angle) * size)
        # 後ろ2点（120度ずらす）
        angle2 = angle + math.radians(140)
        angle3 = angle - math.radians(140)
        p2 = (cx + math.cos(angle2) * size, cy + math.sin(angle2) * size)
        p3 = (cx + math.cos(angle3) * size, cy + math.sin(angle3) * size)
        
        pygame.draw.polygon(self.screen, color, [p1, p2, p3])