"""
全シーン共通の描画基盤
ECSの状態を一切知らず、受け取った値の描画のみを行う低レベルなラッパー。
"""

import pygame
from config import COLORS, FONT_NAMES

class BaseRenderer:
    def __init__(self, screen):
        self.screen = screen
        # 共通フォントの初期化
        font_priority = ",".join(FONT_NAMES)
        self.fonts = {
            'small': pygame.font.SysFont(font_priority, 14),
            'normal': pygame.font.SysFont(font_priority, 20),
            'medium': pygame.font.SysFont(font_priority, 24),
            'large': pygame.font.SysFont(font_priority, 32),
            'notice': pygame.font.SysFont(font_priority, 36)
        }

    def clear(self):
        self.screen.fill(COLORS['BACKGROUND'])

    def present(self):
        pygame.display.flip()

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