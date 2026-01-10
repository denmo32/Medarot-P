"""描画のみを担当するプレゼンテーション層"""

import pygame
from config import COLORS, FONT_NAMES, GAME_PARAMS
from battle.utils import calculate_action_menu_layout

class Renderer:
    """ECSの状態を一切知らず、受け取った値の描画のみを行うクラス"""

    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont(FONT_NAMES, 24)
        self.small_font = pygame.font.SysFont(FONT_NAMES, 14) # 小さめのフォント
        self.title_font = pygame.font.SysFont(FONT_NAMES, 32)
        self.notice_font = pygame.font.SysFont(FONT_NAMES, 36)
        self.icon_radius = 16

    def clear(self):
        self.screen.fill(COLORS['BACKGROUND'])

    def present(self):
        pygame.display.flip()

    def draw_field_guides(self):
        """行動実行ラインなどのガイドを描画"""
        center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
        offset = 40
        h = GAME_PARAMS['SCREEN_HEIGHT']
        
        # プレイヤー側ライン
        p_line_x = center_x - offset
        pygame.draw.line(self.screen, COLORS['GUIDE_LINE'], (p_line_x, 0), (p_line_x, h), 1)
        
        # エネミー側ライン
        e_line_x = center_x + offset
        pygame.draw.line(self.screen, COLORS['GUIDE_LINE'], (e_line_x, 0), (e_line_x, h), 1)

    def draw_home_marker(self, x, y):
        """ホームポジションを示すマーカー（丸印）を描画"""
        # アイコンの待機位置と同じ座標に薄い円を描画
        pygame.draw.circle(self.screen, COLORS['HOME_MARKER'], (int(x), int(y + 20)), 12, 2)

    def draw_character_info(self, x, y, name, icon_x, team_color):
        """名前とATBアイコンを描画"""
        # アイコン
        pygame.draw.circle(self.screen, team_color, (int(icon_x), int(y + 20)), self.icon_radius)
        # 名前（少し上に表示）
        name_txt = self.font.render(name, True, COLORS['TEXT'])
        self.screen.blit(name_txt, (x - 20, y - 25))

    def draw_hp_bars(self, x, y, hp_data_list):
        """
        各パーツのHP情報を描画
        hp_data_list: List of dict {'label': str, 'current': int, 'max': int, 'ratio': float}
        """
        start_y = y + 45
        bar_width = 80
        bar_height = 10
        row_height = 16
        
        for i, data in enumerate(hp_data_list):
            row_y = start_y + i * row_height
            
            # 部位名 (頭部: )
            label_surf = self.small_font.render(f"{data['label']}:", True, (200, 200, 200))
            self.screen.blit(label_surf, (x - 45, row_y - 2))
            
            # バー背景
            pygame.draw.rect(self.screen, COLORS['HP_BG'], (x, row_y, bar_width, bar_height))
            
            # バー中身（統一色）
            fill_w = int(bar_width * max(0, min(1.0, data['ratio'])))
            pygame.draw.rect(self.screen, COLORS['HP_GAUGE'], (x, row_y, fill_w, bar_height))
            
            # 枠線
            pygame.draw.rect(self.screen, (150, 150, 150), (x, row_y, bar_width, bar_height), 1)
            
            # 数値 (50/50)
            val_text = f"{data['current']}/{data['max']}"
            val_surf = self.small_font.render(val_text, True, COLORS['TEXT'])
            self.screen.blit(val_surf, (x + bar_width + 5, row_y - 2))

    def draw_target_marker(self, focused_target, char_positions):
        """
        指定されたターゲットに▼マークを表示
        """
        if focused_target in char_positions:
            pos = char_positions[focused_target]
            # ▼をアイコンの上に表示
            marker_text = self.font.render("▼", True, (255, 255, 0))  # 黄色
            marker_rect = marker_text.get_rect(center=(pos['icon_x'], pos['y'] + 4 - 10))
            self.screen.blit(marker_text, marker_rect)

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
        buttons: List of dict {'label': str, 'sub_label': str, 'enabled': bool}
        selected_index: int (0-3)
        """
        wx, wy = 0, GAME_PARAMS['MESSAGE_WINDOW_Y']
        wh = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']
        ui_cfg = GAME_PARAMS['UI']

        turn_text = self.font.render(f"{turn_name}のターン", True, COLORS['TEXT'])
        self.screen.blit(turn_text, (wx + pad, wy + wh - ui_cfg['TURN_TEXT_Y_OFFSET']))

        button_layout = calculate_action_menu_layout(len(buttons))

        for i, (btn, rect) in enumerate(zip(buttons, button_layout)):
            bx, by, bw, bh = rect['x'], rect['y'], rect['w'], rect['h']
            
            # 背景色
            bg = COLORS['BUTTON_BG'] if btn['enabled'] else COLORS['BUTTON_DISABLED_BG']
            pygame.draw.rect(self.screen, bg, (bx, by, bw, bh))
            
            # 枠線（選択中は黄色、通常は黒）
            border_color = (255, 255, 0) if i == selected_index else COLORS['BUTTON_BORDER']
            border_width = 3 if i == selected_index else 2
            pygame.draw.rect(self.screen, border_color, (bx, by, bw, bh), border_width)
            
            # パーツ名テキスト
            self.screen.blit(self.font.render(btn['label'], True, COLORS['TEXT']), (bx + 10, by + 5))

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