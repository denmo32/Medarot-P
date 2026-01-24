import pygame
from config import COLORS, GAME_PARAMS
from .base_renderer import BaseRenderer

class BattleUIRenderer(BaseRenderer):
    """バトルの情報表示（HUD）やUIメニューの描画を担当"""

    def get_action_menu_layout(self, button_count: int):
        """アクションメニューのボタン配置を計算し、Rectのリストを返す"""
        wx, wy = 0, GAME_PARAMS['MESSAGE_WINDOW_Y']
        wh = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']
        ui_cfg = GAME_PARAMS['UI']

        btn_y = wy + wh - ui_cfg['BTN_Y_OFFSET']
        btn_w, btn_h, btn_pad = ui_cfg['BTN_WIDTH'], ui_cfg['BTN_HEIGHT'], ui_cfg['BTN_PADDING']
        
        layout = []
        for i in range(button_count):
            bx = wx + pad + i * (btn_w + btn_pad)
            layout.append(pygame.Rect(bx, btn_y, btn_w, btn_h))
            
        return layout

    def get_index_at_mouse(self, mouse_pos, button_count):
        """マウス座標からどのボタンがホバーされているか判定する"""
        layout = self.get_action_menu_layout(button_count)
        for i, rect in enumerate(layout):
            if rect.collidepoint(mouse_pos):
                return i
        return None

    def draw_message_window(self, logs, waiting_input):
        wy = GAME_PARAMS['MESSAGE_WINDOW_Y']
        wh = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        ww = GAME_PARAMS['SCREEN_WIDTH']
        pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']

        self.draw_box((0, wy, ww, wh), GAME_PARAMS['MESSAGE_WINDOW_BG_COLOR'], GAME_PARAMS['MESSAGE_WINDOW_BORDER_COLOR'])
        
        for i, log in enumerate(logs):
            self.draw_text(log, (pad, wy + pad + i * 25), font_type='medium')

        if waiting_input:
            ui_cfg = GAME_PARAMS['UI']
            self.draw_text("Zキー or クリックで次に進む", (ww - ui_cfg['NEXT_MSG_X_OFFSET'] - 50, wy + wh - ui_cfg['NEXT_MSG_Y_OFFSET']), font_type='medium')

    def draw_action_menu(self, turn_name, buttons, selected_index):
        wy = GAME_PARAMS['MESSAGE_WINDOW_Y']
        wh = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']
        
        self.draw_text(f"{turn_name}のターン", (pad, wy + wh - GAME_PARAMS['UI']['TURN_TEXT_Y_OFFSET']), font_type='medium')
        
        # 自身のレイアウト定義を使用して描画
        layout = self.get_action_menu_layout(len(buttons))
        
        for i, (btn, rect) in enumerate(zip(buttons, layout)):
            bg = COLORS['BUTTON_BG'] if btn['enabled'] else COLORS['BUTTON_DISABLED_BG']
            border = (255, 255, 0) if i == selected_index else COLORS['BUTTON_BORDER']
            
            self.draw_box(rect, bg, border, 3 if i == selected_index else 2)
            self.draw_text(btn['label'], (rect.x + 10, rect.y + 5), font_type='medium')

    def draw_game_over(self, winner_name):
        overlay = pygame.Surface((GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']), pygame.SRCALPHA)
        overlay.fill(COLORS['NOTICE_BG'])
        self.screen.blit(overlay, (0, 0))

        color = COLORS['PLAYER'] if winner_name == "プレイヤー" else COLORS['ENEMY']
        mid_x, mid_y = GAME_PARAMS['SCREEN_WIDTH'] // 2, GAME_PARAMS['SCREEN_HEIGHT'] // 2
        
        self.draw_text(f"{winner_name}の勝利！", (mid_x, mid_y), color, 'notice', 'center')
        self.draw_text("ESCキーで終了", (mid_x, mid_y + GAME_PARAMS['NOTICE_Y_OFFSET']), COLORS['TEXT'], 'medium', 'center')