"""描画のみを担当するプレゼンテーション層"""

import pygame
from config import COLORS, FONT_NAMES, GAME_PARAMS

class Renderer:
    """ECSの状態を一切知らず、受け取った値の描画のみを行うクラス"""

    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont(FONT_NAMES, 24)
        self.title_font = pygame.font.SysFont(FONT_NAMES, 32)
        self.notice_font = pygame.font.SysFont(FONT_NAMES, 36)
        self.icon_radius = 16

    def clear(self):
        self.screen.fill(COLORS['BACKGROUND'])

    def present(self):
        pygame.display.flip()

    def draw_team_titles(self, player_title: str, enemy_title: str):
        self.screen.blit(self.title_font.render(player_title, True, COLORS['PLAYER']), (50, 50))
        self.screen.blit(self.title_font.render(enemy_title, True, COLORS['ENEMY']), (450, 50))

    def draw_character_info(self, x, y, name, icon_x, team_color):
        """名前とATBアイコンを描画"""
        # アイコン
        pygame.draw.circle(self.screen, team_color, (int(icon_x), int(y + 20)), self.icon_radius)
        # 名前
        name_txt = self.font.render(name, True, COLORS['TEXT'])
        self.screen.blit(name_txt, (x, y - 25))

    def draw_hp_bars(self, x, y, hp_data_list):
        """
        hp_data_list: List of dict {'ratio': float, 'color': tuple}
        """
        for i, data in enumerate(hp_data_list):
            bx = x + i * (GAME_PARAMS['HP_BAR_WIDTH'] + 5)
            by = y + GAME_PARAMS['HP_BAR_Y_OFFSET']
            bw, bh = GAME_PARAMS['HP_BAR_WIDTH'], GAME_PARAMS['HP_BAR_HEIGHT']

            pygame.draw.rect(self.screen, COLORS['HP_BG'], (bx, by, bw, bh))
            fill_w = int(bw * max(0, min(1.0, data['ratio'])))
            pygame.draw.rect(self.screen, data['color'], (bx, by, fill_w, bh))
            pygame.draw.rect(self.screen, COLORS['TEXT'], (bx, by, bw, bh), 1)

    def draw_message_window(self, logs, waiting_input):
        wx, wy = 0, GAME_PARAMS['MESSAGE_WINDOW_Y']
        ww, wh = GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']

        pygame.draw.rect(self.screen, GAME_PARAMS['MESSAGE_WINDOW_BG_COLOR'], (wx, wy, ww, wh))
        pygame.draw.rect(self.screen, GAME_PARAMS['MESSAGE_WINDOW_BORDER_COLOR'], (wx, wy, ww, wh), 2)

        for i, log in enumerate(logs):
            self.screen.blit(self.font.render(log, True, COLORS['TEXT']), (wx + pad, wy + pad + i * 25))

        if waiting_input:
            ui_cfg = GAME_PARAMS['UI']
            txt = self.font.render("Zキー or クリックで次に進む", True, COLORS['TEXT'])
            self.screen.blit(txt, (wx + ww - ui_cfg['NEXT_MSG_X_OFFSET'] - 50, wy + wh - ui_cfg['NEXT_MSG_Y_OFFSET']))

    def draw_action_menu(self, turn_name, buttons, selected_index):
        """
        buttons: List of dict {'label': str, 'enabled': bool}
        selected_index: int (0-3)
        """
        wx, wy = 0, GAME_PARAMS['MESSAGE_WINDOW_Y']
        wh = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']
        ui_cfg = GAME_PARAMS['UI']

        turn_text = self.font.render(f"{turn_name}のターン", True, COLORS['TEXT'])
        self.screen.blit(turn_text, (wx + pad, wy + wh - ui_cfg['TURN_TEXT_Y_OFFSET']))

        btn_y = wy + wh - ui_cfg['BTN_Y_OFFSET']
        btn_w, btn_h, btn_pad = ui_cfg['BTN_WIDTH'], ui_cfg['BTN_HEIGHT'], ui_cfg['BTN_PADDING']

        for i, btn in enumerate(buttons):
            bx = wx + pad + i * (btn_w + btn_pad)
            
            # 背景色
            bg = COLORS['BUTTON_BG'] if btn['enabled'] else COLORS['BUTTON_DISABLED_BG']
            pygame.draw.rect(self.screen, bg, (bx, btn_y, btn_w, btn_h))
            
            # 枠線（選択中は黄色、通常は黒）
            border_color = (255, 255, 0) if i == selected_index else COLORS['BUTTON_BORDER']
            border_width = 3 if i == selected_index else 2
            pygame.draw.rect(self.screen, border_color, (bx, btn_y, btn_w, btn_h), border_width)
            
            # テキスト
            self.screen.blit(self.font.render(btn['label'], True, COLORS['TEXT']), (bx + 10, btn_y + 10))

    def draw_game_over(self, winner_name):
        overlay = pygame.Surface((GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']), pygame.SRCALPHA)
        overlay.fill(COLORS['NOTICE_BG'])
        self.screen.blit(overlay, (0, 0))

        color = COLORS['PLAYER'] if winner_name == "プレイヤー" else COLORS['ENEMY']
        res_text = self.notice_font.render(f"{winner_name}の勝利！", True, color)
        tr = res_text.get_rect(center=(GAME_PARAMS['SCREEN_WIDTH'] // 2, GAME_PARAMS['SCREEN_HEIGHT'] // 2))
        self.screen.blit(res_text, tr)
        
        exit_txt = self.font.render("ESCキーで終了", True, COLORS['TEXT'])
        er = exit_txt.get_rect(center=(GAME_PARAMS['SCREEN_WIDTH'] // 2, GAME_PARAMS['SCREEN_HEIGHT'] // 2 + GAME_PARAMS['NOTICE_Y_OFFSET']))
        self.screen.blit(exit_txt, er)