"""メッセージウィンドウ、アクションメニュー、リザルトの描画"""

import pygame
from ui.config import COLORS, UI_PARAMS
from .layout_utils import calculate_action_menu_layout

class UIPanelRenderer:
    def __init__(self, master):
        self.m = master

    def render(self, snapshot):
        if snapshot.log_window.is_active:
            self._render_log_window(snapshot.log_window)
        if snapshot.action_menu.is_active:
            self._render_action_menu(snapshot.action_menu)
        if snapshot.game_over.is_active:
            self._render_game_over(snapshot.game_over)

    def _render_log_window(self, data):
        sw, sh = self.m.get_screen_size()
        
        wy = self.m.scale_y(UI_PARAMS['MESSAGE_WINDOW_Y_RATIO'])
        wh = self.m.scale_y(UI_PARAMS['MESSAGE_WINDOW_HEIGHT_RATIO'])
        pad = self.m.scale_x(UI_PARAMS['MESSAGE_WINDOW_PADDING_RATIO'])
        
        line_h = int(sh * 0.04)

        self.m.draw_box((0, wy, sw, wh), UI_PARAMS['MESSAGE_WINDOW_BG_COLOR'], UI_PARAMS['MESSAGE_WINDOW_BORDER_COLOR'])
        for i, log in enumerate(data.logs):
            self.m.draw_text(log, (pad, wy + pad + i * line_h), font_type='medium')

        if data.show_input_guidance:
            next_off_x = self.m.scale_x(0.3)
            next_off_y = self.m.scale_y(0.05)
            self.m.draw_text("Zキー or クリックで次に進む", 
                           (sw - next_off_x, wy + wh - next_off_y), font_type='medium')

    def _render_action_menu(self, data):
        sw, sh = self.m.get_screen_size()
        wy = self.m.scale_y(UI_PARAMS['MESSAGE_WINDOW_Y_RATIO'])
        wh = self.m.scale_y(UI_PARAMS['MESSAGE_WINDOW_HEIGHT_RATIO'])
        pad = self.m.scale_x(UI_PARAMS['MESSAGE_WINDOW_PADDING_RATIO'])
        
        name_y_offset = int(sh * 0.16)
        
        self.m.draw_text(f"{data.actor_name}", (pad, wy + wh - name_y_offset), font_type='medium')
        
        layout = calculate_action_menu_layout(len(data.buttons), (sw, sh))
        
        for i, (btn, rect) in enumerate(zip(data.buttons, layout)):
            bg = COLORS['BUTTON_BG'] if btn.enabled else COLORS['BUTTON_DISABLED_BG']
            border = (255, 255, 0) if i == data.selected_index else COLORS['BUTTON_BORDER']
            self.m.draw_box(rect, bg, border, 3 if i == data.selected_index else 2)
            self.m.draw_text(btn.label, rect.center, font_type='medium', align='center')

    def _render_game_over(self, data):
        sw, sh = self.m.get_screen_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill(COLORS['NOTICE_BG'])
        self.m.screen.blit(overlay, (0, 0))

        color = COLORS['PLAYER'] if data.winner == "プレイヤー" else COLORS['ENEMY']
        mid_x, mid_y = sw // 2, sh // 2
        
        # BaseRendererに移設したメソッドを使用。強調のためlarge/centerを指定
        self.m.draw_text_with_outline(f"{data.winner}の勝利！", mid_x, mid_y, color, 'notice', 'center')
        
        notice_off_y = int(sh * 0.08)
        self.m.draw_text("ESCキーで終了", (mid_x, mid_y + notice_off_y), COLORS['TEXT'], 'medium', 'center')