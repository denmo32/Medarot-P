"""タイトル画面専用のレンダラー（テーマ色・ViewModel対応）"""
import pygame
from features.title.view_models import TitleViewModel
from ui.config import FONT_NAMES
from ui.base.renderer import BaseRenderer
from ui.base.fonts import FontProvider
from ui.title.layout import calculate_button_layouts


class TitleRenderer(BaseRenderer):
    """タイトル画面の描画を担当"""

    def _init_custom_fonts(self):
        scale = self.ui_scale
        custom_font_path = 'assets/fonts/851Gkktt_005.ttf'
        fallback_font_path = FONT_NAMES[0] if FONT_NAMES else 'freesansbold.ttf'

        try:
            self.title_font = FontProvider.get(custom_font_path, 80, scale)
            self.p_font = FontProvider.get(custom_font_path, 128, scale)
        except (OSError, pygame.error):
            self.title_font = FontProvider.get(fallback_font_path, 48, scale)
            self.p_font = FontProvider.get(fallback_font_path, 72, scale)

        self.button_font = FontProvider.get(fallback_font_path, 32, scale)
        self.title_surface = self._create_title_surface()

    def render(self, model: TitleViewModel):
        self.clear()
        sw, sh = self.get_screen_size()

        title_rect = self.title_surface.get_rect(center=(sw // 2, int(sh * 0.25)))
        self.screen.blit(self.title_surface, title_rect)

        layouts = calculate_button_layouts((sw, sh), model.buttons)

        for i, button in enumerate(model.buttons):
            rect = layouts[i]
            self._draw_button(rect, button.text, button.is_selected)

        self.present()

    def _draw_button(self, rect: pygame.Rect, text: str, is_selected: bool):
        pygame.draw.rect(self.screen, self.theme.button_bg, rect)

        border_color = self.theme.target_marker if is_selected else self.theme.button_border
        border_width = 3 if is_selected else 2
        pygame.draw.rect(self.screen, border_color, rect, border_width)

        text_surface = self.button_font.render(text, True, self.theme.text)
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

    def _create_medarot_surface(self) -> pygame.Surface:
        text_medarot = "メダロット"
        medarot_base = self.title_font.render(text_medarot, True, (255, 255, 255))
        mw, mh = medarot_base.get_size()

        m_outer_border_color = (0, 0, 100)
        m_outer_border_size = 7
        m_inner_border_color = (255, 255, 255)
        m_inner_border_size = 2

        medarot_full = pygame.Surface((mw + m_outer_border_size * 2, mh + m_outer_border_size * 2), pygame.SRCALPHA)

        m_outer_surf = self.title_font.render(text_medarot, True, m_outer_border_color)
        for dx in range(-m_outer_border_size, m_outer_border_size + 1):
            for dy in range(-m_outer_border_size, m_outer_border_size + 1):
                medarot_full.blit(m_outer_surf, (dx + m_outer_border_size, dy + m_outer_border_size))

        m_inner_surf = self.title_font.render(text_medarot, True, m_inner_border_color)
        for dx in range(-m_inner_border_size, m_inner_border_size + 1):
            for dy in range(-m_inner_border_size, m_inner_border_size + 1):
                medarot_full.blit(m_inner_surf, (dx + m_outer_border_size, dy + m_outer_border_size))

        gradient = pygame.Surface((mw, mh))
        red = (255, 0, 0)
        yellow = (255, 255, 0)
        for x in range(mw):
            ratio = x / mw
            if ratio < 0.5:
                t = ratio * 2
                color = (int(red[0] + (yellow[0] - red[0]) * t),
                         int(red[1] + (yellow[1] - red[1]) * t),
                         int(red[2] + (yellow[2] - red[2]) * t))
            else:
                t = (ratio - 0.5) * 2
                color = (int(yellow[0] + (red[0] - yellow[0]) * t),
                         int(yellow[1] + (red[1] - yellow[1]) * t),
                         int(yellow[2] + (red[2] - yellow[2]) * t))
            pygame.draw.line(gradient, color, (x, 0), (x, mh))

        gradient_text = pygame.Surface((mw, mh), pygame.SRCALPHA)
        gradient_text.blit(gradient, (0, 0))
        gradient_text.blit(medarot_base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        medarot_full.blit(gradient_text, (m_outer_border_size, m_outer_border_size))
        return medarot_full

    def _create_p_surface(self) -> pygame.Surface:
        text_p = "P"
        p_color = (0, 200, 255)
        border_color = (255, 255, 255)
        border_size = 4

        base_p = self.p_font.render(text_p, True, p_color)
        pw, ph = base_p.get_size()

        p_surface = pygame.Surface((pw + border_size * 2, ph + border_size * 2), pygame.SRCALPHA)

        border_p = self.p_font.render(text_p, True, border_color)
        for dx in range(-border_size, border_size + 1):
            for dy in range(-border_size, border_size + 1):
                if dx == 0 and dy == 0:
                    continue
                p_surface.blit(border_p, (dx + border_size, dy + border_size))

        p_surface.blit(base_p, (border_size, border_size))
        return p_surface

    def _create_title_surface(self) -> pygame.Surface:
        medarot_surf = self._create_medarot_surface()
        p_surf = self._create_p_surface()

        total_width = medarot_surf.get_width() + p_surf.get_width() + 10
        max_height = max(medarot_surf.get_height(), p_surf.get_height())

        combined_surface = pygame.Surface((total_width, max_height), pygame.SRCALPHA)

        medarot_y = (max_height - medarot_surf.get_height()) // 2
        p_y = (max_height - p_surf.get_height()) // 2

        combined_surface.blit(medarot_surf, (0, medarot_y))
        combined_surface.blit(p_surf, (medarot_surf.get_width() + 10, p_y))

        return combined_surface