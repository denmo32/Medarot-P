"""
全シーン共通の描画基盤
受け取った値の描画のみを行う低レベルなラッパー（型安全・Theme一元化）。
"""
from typing import Optional, Tuple
import pygame
from ui.config import Theme, DEFAULT_THEME, FONT_NAMES, COMMAND_BUTTON_FONT_NAME, SCREEN_HEIGHT
from ui.base.fonts import FontProvider


class BaseRenderer:
    def __init__(self, screen: pygame.Surface, theme: Theme = DEFAULT_THEME):
        self.screen = screen
        self.theme = theme
        self._last_scale: Optional[float] = None
        self._ensure_fonts()

    @property
    def ui_scale(self) -> float:
        """現在の画面高さに基づくスケーリング係数"""
        return self.screen.get_height() / SCREEN_HEIGHT

    def _ensure_fonts(self):
        """スケールが変更された場合、フォントを再生成する。"""
        current_scale = self.ui_scale
        if current_scale != self._last_scale:
            self._init_fonts()
            self._init_custom_fonts()
            self._last_scale = current_scale

    def _init_custom_fonts(self):
        """サブクラスが独自フォントを追加する際のフック"""
        pass

    def scaled(self, value: float) -> int:
        """基準解像度(高さ)に基づく値を現在の解像度にスケーリングして整数で返す"""
        return int(value * self.ui_scale)

    def _init_fonts(self):
        """フォントの初期化"""
        font_path = FONT_NAMES[0] if FONT_NAMES else 'freesansbold.ttf'
        button_font_path = COMMAND_BUTTON_FONT_NAME
        scale = self.ui_scale

        self.fonts = {
            'tiny': FontProvider.get(font_path, 11, scale),
            'small': FontProvider.get(font_path, 14, scale),
            'normal': FontProvider.get(font_path, 20, scale),
            'medium': FontProvider.get(font_path, 24, scale),
            'large': FontProvider.get(font_path, 32, scale),
            'notice': FontProvider.get(font_path, 36, scale),
            'command_button': FontProvider.get(button_font_path, 24, scale),
            'command_button_focus': FontProvider.get(button_font_path, 28, scale)
        }

    def clear(self):
        self._ensure_fonts()
        self.screen.fill(self.theme.background)

    def present(self):
        pygame.display.flip()

    # --- 座標変換ユーティリティ ---

    def get_screen_size(self) -> Tuple[int, int]:
        return self.screen.get_width(), self.screen.get_height()

    def to_px(self, rx: float, ry: float) -> Tuple[int, int]:
        w, h = self.get_screen_size()
        return int(rx * w), int(ry * h)

    def scale_x(self, ratio: float) -> int:
        return int(ratio * self.screen.get_width())

    def scale_y(self, ratio: float) -> int:
        return int(ratio * self.screen.get_height())

    # --- 描画プリミティブ ---

    def draw_box(
        self,
        rect: pygame.Rect | Tuple[int, int, int, int],
        bg_color: Tuple[int, ...],
        border_color: Optional[Tuple[int, ...]] = None,
        border_width: int = 2,
    ):
        pygame.draw.rect(self.screen, bg_color, rect)
        if border_color:
            pygame.draw.rect(self.screen, border_color, rect, border_width)

    def draw_pipe_box(
        self,
        rect: pygame.Rect | Tuple[int, int, int, int],
        bg_color: Tuple[int, ...],
        pipe_color: Tuple[int, ...],
        joint_color: Tuple[int, ...],
    ):
        x, y, w, h = rect
        pygame.draw.rect(self.screen, bg_color, rect)

        thick = self.scaled(6)
        pygame.draw.rect(self.screen, pipe_color, rect, thick)

        js = self.scaled(12)
        joints = [
            (x, y), (x + w - js, y), (x, y + h - js), (x + w - js, y + h - js)
        ]
        for jx, jy in joints:
            pygame.draw.rect(self.screen, joint_color, (jx, jy, js, js))
            pygame.draw.rect(self.screen, (0, 0, 0), (jx, jy, js, js), 1)

    def draw_text(
        self,
        text: str,
        pos: Tuple[int, int],
        color: Optional[Tuple[int, ...]] = None,
        font_type: str = 'normal',
        align: str = 'left',
    ):
        self._ensure_fonts()
        text_color = color or self.theme.text
        surf = self.fonts[font_type].render(str(text), True, text_color)
        rect = surf.get_rect()
        if align == 'left':
            rect.topleft = pos
        elif align == 'center':
            rect.center = pos
        elif align == 'right':
            rect.topright = pos
        self.screen.blit(surf, rect)

    def draw_text_with_outline(
        self,
        text: str,
        x: int,
        y: int,
        color: Optional[Tuple[int, ...]] = None,
        font_type: str = 'normal',
        align: str = 'left',
        outline_color: Tuple[int, ...] = (0, 0, 0),
    ):
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            self.draw_text(text, (x + ox, y + oy), outline_color, font_type, align)
        self.draw_text(text, (x, y), color, font_type, align)

    def draw_bar(
        self,
        rect: pygame.Rect | Tuple[int, int, int, int],
        ratio: float,
        bg_color: Tuple[int, ...],
        fg_color: Tuple[int, ...],
        border_color: Optional[Tuple[int, ...]] = (150, 150, 150),
    ):
        pygame.draw.rect(self.screen, bg_color, rect)
        fill_w = int(rect[2] * max(0.0, min(1.0, ratio)))
        if fill_w > 0:
            pygame.draw.rect(self.screen, fg_color, (rect[0], rect[1], fill_w, rect[3]))
        if border_color:
            pygame.draw.rect(self.screen, border_color, rect, 1)

    def draw_lightning(self, pos: Tuple[float, float], size: float, color: Tuple[int, ...]):
        cx, cy = pos
        s = size / 20.0
        pts = [
            (cx + 4*s,  cy - 12*s),
            (cx - 6*s,  cy + 2*s),
            (cx - 1*s,  cy + 2*s),
            (cx - 4*s,  cy + 12*s),
            (cx + 6*s,  cy - 2*s),
            (cx + 1*s,  cy - 2*s),
        ]
        pygame.draw.polygon(self.screen, color, pts)