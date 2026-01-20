import pygame
from config import COLORS, GAME_PARAMS
from .base_renderer import BaseRenderer
from battle.utils import calculate_action_menu_layout

class BattleUIRenderer(BaseRenderer):
    """バトルの情報表示（HUD）やUIメニューの描画を担当"""

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
        
        for i, (btn, rect_dict) in enumerate(zip(buttons, calculate_action_menu_layout(len(buttons)))):
            rect = (rect_dict['x'], rect_dict['y'], rect_dict['w'], rect_dict['h'])
            bg = COLORS['BUTTON_BG'] if btn['enabled'] else COLORS['BUTTON_DISABLED_BG']
            border = (255, 255, 0) if i == selected_index else COLORS['BUTTON_BORDER']
            
            self.draw_box(rect, bg, border, 3 if i == selected_index else 2)
            self.draw_text(btn['label'], (rect[0] + 10, rect[1] + 5), font_type='medium')

    def draw_game_over(self, winner_name):
        overlay = pygame.Surface((GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']), pygame.SRCALPHA)
        overlay.fill(COLORS['NOTICE_BG'])
        self.screen.blit(overlay, (0, 0))

        color = COLORS['PLAYER'] if winner_name == "プレイヤー" else COLORS['ENEMY']
        mid_x, mid_y = GAME_PARAMS['SCREEN_WIDTH'] // 2, GAME_PARAMS['SCREEN_HEIGHT'] // 2
        
        self.draw_text(f"{winner_name}の勝利！", (mid_x, mid_y), color, 'notice', 'center')
        self.draw_text("ESCキーで終了", (mid_x, mid_y + GAME_PARAMS['NOTICE_Y_OFFSET']), COLORS['TEXT'], 'medium', 'center')
