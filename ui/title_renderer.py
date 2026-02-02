"""タイトル画面専用のレンダラー"""

import pygame
from ui.config import COLORS, FONT_NAMES
from ui.base.renderer import BaseRenderer
from core.utils import resource_path

class TitleRenderer(BaseRenderer):
    """タイトル画面の描画を担当（相対座標対応）"""

    def __init__(self, screen):
        super().__init__(screen)
        
        # フォント読み込み（サイズは描画時に調整するため、ここでは大きめでロードするか、scale対応が必要）
        # BaseRendererのinit_fontsで標準フォントは作られるが、タイトル専用は別途管理
        self._init_custom_fonts()

    def _init_custom_fonts(self):
        # 画面サイズに応じたスケーリング
        scale = self.ui_scale
        
        try:
            self.title_font = pygame.font.Font(resource_path('ui/assets/fonts/851Gkktt_005.ttf'), int(80 * scale))
            self.p_font = pygame.font.Font(resource_path('ui/assets/fonts/851Gkktt_005.ttf'), int(128 * scale))
        except OSError:
            font_path = resource_path(FONT_NAMES[0]) if FONT_NAMES else resource_path('freesansbold.ttf')
            self.title_font = pygame.font.Font(font_path, int(48 * scale))
            self.p_font = pygame.font.Font(font_path, int(72 * scale))

        font_path = resource_path(FONT_NAMES[0]) if FONT_NAMES else resource_path('freesansbold.ttf')
        self.button_font = pygame.font.Font(font_path, int(32 * scale))
        
        # タイトルロゴ再生成
        self.title_surface = self._create_title_surface()

    def render(self, ui_data):
        self.clear()
        
        # リサイズ検知が必要な場合、ここでフォント再生成などが要るが、
        # 簡易的にロゴ位置とボタン位置のみ動的計算する
        
        sw, sh = self.get_screen_size()

        # タイトルロゴ配置 (上から25%)
        title_rect = self.title_surface.get_rect(center=(sw // 2, int(sh * 0.25)))
        self.screen.blit(self.title_surface, title_rect)
        
        # ボタン
        buttons = ui_data.get('buttons', [])
        selected_index = ui_data.get('selected_index', 0)
        
        for i, button in enumerate(buttons):
            # Layout定義に基づいて矩形計算
            layout = button['layout']
            w, h = sw * layout['w_ratio'], sh * layout['h_ratio']
            x = sw * layout['cx'] - w / 2
            y = sh * layout['cy'] - h / 2
            rect = pygame.Rect(x, y, w, h)
            
            self._draw_button(rect, button['text'], i == selected_index)
            
        self.present()

    def _draw_button(self, rect, text, is_selected):
        pygame.draw.rect(self.screen, COLORS['BUTTON_BG'], rect)
        
        border_color = (255, 255, 0) if is_selected else COLORS['BUTTON_BORDER']
        border_width = 3 if is_selected else 2
        pygame.draw.rect(self.screen, border_color, rect, border_width)

        text_surface = self.button_font.render(text, True, COLORS['TEXT'])
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

    def _create_title_surface(self):
        """グラデーションタイトルと装飾されたPを作成"""
        # 1. "メダロット" の作成
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

        # 2. "P" の作成
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
                if dx == 0 and dy == 0: continue
                p_surface.blit(border_p, (dx + border_size, dy + border_size))
        
        p_surface.blit(base_p, (border_size, border_size))
        
        # 3. 結合
        total_width = medarot_full.get_width() + p_surface.get_width() + 10
        max_height = max(medarot_full.get_height(), p_surface.get_height())
        
        combined_surface = pygame.Surface((total_width, max_height), pygame.SRCALPHA)
        
        medarot_y = (max_height - medarot_full.get_height()) // 2
        p_y = (max_height - p_surface.get_height()) // 2
        
        combined_surface.blit(medarot_full, (0, medarot_y))
        combined_surface.blit(p_surface, (medarot_full.get_width() + 10, p_y))
        
        return combined_surface