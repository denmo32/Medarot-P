"""タイトル画面専用のレンダラー"""

import pygame
from ui.config import COLORS, FONT_NAMES, SCREEN_WIDTH
from ui.base.renderer import BaseRenderer

class TitleRenderer(BaseRenderer):
    """タイトル画面の描画を担当"""

    def __init__(self, screen):
        super().__init__(screen)
        
        # タイトル固有のフォント
        try:
            self.title_font = pygame.font.Font('ui/assets/fonts/851Gkktt_005.ttf', 80)
            self.p_font = pygame.font.Font('ui/assets/fonts/851Gkktt_005.ttf', 128)
        except OSError:
            print("Warning: Custom font not found, falling back to system font.")
            font_name = FONT_NAMES[0] if FONT_NAMES else None
            self.title_font = pygame.font.SysFont(font_name, 48)
            self.p_font = pygame.font.SysFont(font_name, 72)
            
        self.button_font = pygame.font.SysFont(",".join(FONT_NAMES), 32)
        
        # 静的なタイトルロゴは初期化時に作成してキャッシュする
        self.title_surface = self._create_title_surface()

    def render(self, ui_data):
        """
        ui_data: {
            'buttons': [{'rect': Rect, 'text': str, ...}, ...],
            'selected_index': int
        }
        """
        self.clear()
        
        # タイトルロゴ
        title_rect = self.title_surface.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(self.title_surface, title_rect)
        
        # ボタン
        buttons = ui_data.get('buttons', [])
        selected_index = ui_data.get('selected_index', 0)
        
        for i, button in enumerate(buttons):
            self._draw_button(button, i == selected_index)
            
        self.present()

    def _draw_button(self, button, is_selected):
        rect = button['rect']
        
        # 背景
        pygame.draw.rect(self.screen, COLORS['BUTTON_BG'], rect)
        
        # 枠線（選択時は黄色で太く）
        border_color = (255, 255, 0) if is_selected else COLORS['BUTTON_BORDER']
        border_width = 3 if is_selected else 2
        pygame.draw.rect(self.screen, border_color, rect, border_width)

        # テキスト
        text_surface = self.button_font.render(button['text'], True, COLORS['TEXT'])
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

    def _create_title_surface(self):
        """グラデーションタイトルと装飾されたPを作成"""
        # 1. "メダロット" の作成
        text_medarot = "メダロット"
        medarot_base = self.title_font.render(text_medarot, True, (255, 255, 255))
        mw, mh = medarot_base.get_size()
        
        # 縁取りの設定 (外側：濃い青、内側：白)
        m_outer_border_color = (0, 0, 100)
        m_outer_border_size = 7
        m_inner_border_color = (255, 255, 255)
        m_inner_border_size = 2
        
        # メダロット部分の土台サーフェス
        medarot_full = pygame.Surface((mw + m_outer_border_size * 2, mh + m_outer_border_size * 2), pygame.SRCALPHA)
        
        # 外側の縁取りを描画 (青)
        m_outer_surf = self.title_font.render(text_medarot, True, m_outer_border_color)
        for dx in range(-m_outer_border_size, m_outer_border_size + 1):
            for dy in range(-m_outer_border_size, m_outer_border_size + 1):
                medarot_full.blit(m_outer_surf, (dx + m_outer_border_size, dy + m_outer_border_size))

        # 内側の縁取りを描画 (白)
        m_inner_surf = self.title_font.render(text_medarot, True, m_inner_border_color)
        for dx in range(-m_inner_border_size, m_inner_border_size + 1):
            for dy in range(-m_inner_border_size, m_inner_border_size + 1):
                medarot_full.blit(m_inner_surf, (dx + m_outer_border_size, dy + m_outer_border_size)) 
        
        # グラデーション文字の作成
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
        
        # 縁取りの上にグラデーション文字を重ねる
        medarot_full.blit(gradient_text, (m_outer_border_size, m_outer_border_size))

        # 2. "P" の作成（縁取り付き）
        text_p = "P"
        p_color = (0, 200, 255) # Cyan/Blue
        border_color = (255, 255, 255) # White
        border_size = 4
        
        base_p = self.p_font.render(text_p, True, p_color)
        pw, ph = base_p.get_size()
        
        # 縁取り用サーフェス
        p_surface = pygame.Surface((pw + border_size * 2, ph + border_size * 2), pygame.SRCALPHA)
        
        # 8方向にずらして描画して縁取りを作る
        border_p = self.p_font.render(text_p, True, border_color)
        for dx in range(-border_size, border_size + 1):
            for dy in range(-border_size, border_size + 1):
                if dx == 0 and dy == 0: continue
                p_surface.blit(border_p, (dx + border_size, dy + border_size))
        
        # 中心に本体を描画
        p_surface.blit(base_p, (border_size, border_size))
        
        # 3. 結合
        total_width = medarot_full.get_width() + p_surface.get_width() + 10 # 10px spacing
        max_height = max(medarot_full.get_height(), p_surface.get_height())
        
        combined_surface = pygame.Surface((total_width, max_height), pygame.SRCALPHA)
        
        # 配置（上下中央揃え）
        medarot_y = (max_height - medarot_full.get_height()) // 2
        p_y = (max_height - p_surface.get_height()) // 2
        
        combined_surface.blit(medarot_full, (0, medarot_y))
        combined_surface.blit(p_surface, (medarot_full.get_width() + 10, p_y))
        
        return combined_surface
