"""メッセージウィンドウ、アクションメニュー、リザルトの描画"""

import pygame
from ui.config import COLORS, UI_PARAMS, SCREEN_WIDTH, SCREEN_HEIGHT
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
        wy, wh = UI_PARAMS['MESSAGE_WINDOW_Y'], UI_PARAMS['MESSAGE_WINDOW_HEIGHT']
        ww, pad = SCREEN_WIDTH, UI_PARAMS['MESSAGE_WINDOW_PADDING']

        self.m.draw_box((0, wy, ww, wh), UI_PARAMS['MESSAGE_WINDOW_BG_COLOR'], UI_PARAMS['MESSAGE_WINDOW_BORDER_COLOR'])
        for i, log in enumerate(data.logs):
            self.m.draw_text(log, (pad, wy + pad + i * 25), font_type='medium')

        if data.show_input_guidance:
            ui_cfg = UI_PARAMS['UI']
            self.m.draw_text("Zキー or クリックで次に進む", 
                           (ww - ui_cfg['NEXT_MSG_X_OFFSET'] - 50, wy + wh - ui_cfg['NEXT_MSG_Y_OFFSET']), font_type='medium')

    def _render_action_menu(self, data):
        wy, wh = UI_PARAMS['MESSAGE_WINDOW_Y'], UI_PARAMS['MESSAGE_WINDOW_HEIGHT']
        pad = UI_PARAMS['MESSAGE_WINDOW_PADDING']
        self.m.draw_text(f"{data.actor_name}", (pad, wy + wh - UI_PARAMS['UI']['TURN_TEXT_Y_OFFSET']), font_type='medium')
        
        layout = calculate_action_menu_layout(len(data.buttons))
        for i, (btn, rect) in enumerate(zip(data.buttons, layout)):
            bg = COLORS['BUTTON_BG'] if btn.enabled else COLORS['BUTTON_DISABLED_BG']
            border = (255, 255, 0) if i == data.selected_index else COLORS['BUTTON_BORDER']
            self.m.draw_box(rect, bg, border, 3 if i == data.selected_index else 2)
            # 中央揃えでテキストを描画
            self.m.draw_text(btn.label, rect.center, font_type='medium', align='center')

    def _render_game_over(self, data):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(COLORS['NOTICE_BG'])
        self.m.screen.blit(overlay, (0, 0))

        color = COLORS['PLAYER'] if data.winner == "プレイヤー" else COLORS['ENEMY']
        mid_x, mid_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        self.m.draw_text_with_outline(f"{data.winner}の勝利！", mid_x, mid_y, color, 'notice')
        self.m.draw_text("ESCキーで終了", (mid_x, mid_y + UI_PARAMS['NOTICE_Y_OFFSET']), COLORS['TEXT'], 'medium', 'center')