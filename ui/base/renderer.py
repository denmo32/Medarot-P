"""
全シーン共通の描画基盤
ECSの状態を一切知らず、受け取った値の描画のみを行う低レベルなラッパー。
"""

import pygame
from ui.config import COLORS, FONT_NAMES, ACTION_BUTTON_FONT_NAME, SCREEN_HEIGHT
from ui.base.fonts import FontProvider
from core.utils import resource_path

class BaseRenderer:
    def __init__(self, screen):
        self.screen = screen
        self._last_scale = self.ui_scale
        self._init_fonts()

    @property
    def ui_scale(self) -> float:
        """現在の画面高さに基づくスケーリング係数"""
        return self.screen.get_height() / SCREEN_HEIGHT

    def _ensure_fonts(self):
        """スケールが変更された場合、フォントを再生成する"""
        current_scale = self.ui_scale
        if current_scale != self._last_scale:
            self._init_fonts()
            self._last_scale = current_scale

    def scaled(self, value: float) -> int:
        """基準解像度(高さ)に基づく値を現在の解像度にスケーリングして整数で返す"""
        self._ensure_fonts() # フォントの新鮮さを保証
        return int(value * self.ui_scale)

    def _init_fonts(self):
        """フォントの初期化。画面サイズに応じたスケーリングはここで行う"""
        font_path = FONT_NAMES[0] if FONT_NAMES else 'freesansbold.ttf'
        button_font_path = ACTION_BUTTON_FONT_NAME
        
        # フォントサイズ設定 (現在のスケールで生成)
        scale = self.ui_scale

        self.fonts = {
            'small': FontProvider.get(font_path, 14, scale),
            'normal': FontProvider.get(font_path, 20, scale),
            'medium': FontProvider.get(font_path, 24, scale),
            'large': FontProvider.get(font_path, 32, scale),
            'notice': FontProvider.get(font_path, 36, scale),
            'action_button': FontProvider.get(button_font_path, 24, scale),
            'action_button_focus': FontProvider.get(button_font_path, 28, scale)
        }

    def clear(self):
        self._ensure_fonts()
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
        self._ensure_fonts()
        pygame.draw.rect(self.screen, bg_color, rect)
        if border_color:
            pygame.draw.rect(self.screen, border_color, rect, border_width)

    def draw_pipe_box(self, rect, bg_color, pipe_color, joint_color):
        """パイプ装飾付きのボックスを描画"""
        self._ensure_fonts()
        x, y, w, h = rect
        pygame.draw.rect(self.screen, bg_color, rect)
        
        thick = self.scaled(6)
        # パイプ枠を先に描画
        pygame.draw.rect(self.screen, pipe_color, rect, thick)
        
        # ジョイントをパイプの上に重ねて描画
        js = self.scaled(12) # ジョイントのサイズ
        # 四隅だけにジョイントを配置
        joints = [
            (x, y), (x + w - js, y), (x, y + h - js), (x + w - js, y + h - js)
        ]
        for jx, jy in joints:
            pygame.draw.rect(self.screen, joint_color, (jx, jy, js, js))
            # 最後に黒い縁取り
            pygame.draw.rect(self.screen, (0, 0, 0), (jx, jy, js, js), 1)

    def draw_text(self, text, pos, color=COLORS['TEXT'], font_type='normal', align='left'):
        """テキストを描画"""
        self._ensure_fonts()
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
        self._ensure_fonts()
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
        self._ensure_fonts()
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

    def draw_lightning(self, pos, size, color):
        """稲妻記号を描画"""
        self._ensure_fonts()
        cx, cy = pos
        s = size / 20.0
        # 稲妻のポリゴン頂点
        pts = [
            (cx + 4*s,  cy - 12*s),
            (cx - 6*s,  cy + 2*s),
            (cx - 1*s,  cy + 2*s),
            (cx - 4*s,  cy + 12*s),
            (cx + 6*s,  cy - 2*s),
            (cx + 1*s,  cy - 2*s),
        ]
        pygame.draw.polygon(self.screen, color, pts)
