"""描画のみを担当するプレゼンテーション層"""

import pygame
import math
from config import COLORS, FONT_NAMES, GAME_PARAMS

class Renderer:
    """
    低レベルな描画プリミティブと、共通のUIパーツを提供する基底クラス。
    ECSの状態を一切知らず、受け取った値の描画のみを行う。
    """

    def __init__(self, screen):
        self.screen = screen
        # 共通フォントの初期化
        self.fonts = {
            'small': pygame.font.SysFont(FONT_NAMES, 14),
            'normal': pygame.font.SysFont(FONT_NAMES, 20),
            'medium': pygame.font.SysFont(FONT_NAMES, 24),
            'large': pygame.font.SysFont(FONT_NAMES, 32),
            'notice': pygame.font.SysFont(FONT_NAMES, 36)
        }

    def clear(self):
        self.screen.fill(COLORS['BACKGROUND'])

    def present(self):
        pygame.display.flip()

    # --- 描画プリミティブ ---

    def draw_box(self, rect, bg_color, border_color=None, border_width=2):
        """背景と枠線を持つ矩形を描画"""
        pygame.draw.rect(self.screen, bg_color, rect)
        if border_color:
            pygame.draw.rect(self.screen, border_color, rect, border_width)

    def draw_text(self, text, pos, color=COLORS['TEXT'], font_type='normal', align='left'):
        """テキストを描画"""
        surf = self.fonts[font_type].render(str(text), True, color)
        rect = surf.get_rect()
        if align == 'left':
            rect.topleft = pos
        elif align == 'center':
            rect.center = pos
        elif align == 'right':
            rect.topright = pos
        self.screen.blit(surf, rect)

    def draw_bar(self, rect, ratio, bg_color, fg_color, border_color=(150, 150, 150)):
        """プログレスバーを描画"""
        # 背景
        pygame.draw.rect(self.screen, bg_color, rect)
        # 中身
        fill_w = int(rect[2] * max(0, min(1.0, ratio)))
        if fill_w > 0:
            pygame.draw.rect(self.screen, fg_color, (rect[0], rect[1], fill_w, rect[3]))
        # 枠線
        if border_color:
            pygame.draw.rect(self.screen, border_color, rect, 1)

    def draw_flow_line(self, start_pos, end_pos, time_offset, color=(255, 255, 0)):
        """始点から終点へ向かうフローライン（▶▶▶）を描画する"""
        sx, sy = start_pos
        ex, ey = end_pos
        
        dx = ex - sx
        dy = ey - sy
        dist = math.hypot(dx, dy)
        if dist < 1: return

        angle = math.atan2(dy, dx)
        
        # 三角形の数と間隔
        spacing = 30
        count = int(dist / spacing)
        
        # 時間経過でオフセットを移動させる (0 -> spacing)
        move_offset = (time_offset * 100) % spacing
        
        for i in range(count):
            # 現在の位置（始点からの距離）
            d = i * spacing + move_offset
            if d > dist: continue
            
            # 座標計算
            px = sx + math.cos(angle) * d
            py = sy + math.sin(angle) * d
            
            # 三角形を描画（進行方向に向ける）
            self._draw_triangle((px, py), angle, 8, color)
            
        # 簡易的な四隅マーカー
        m_size = 20
        pygame.draw.lines(self.screen, color, False, [
            (ex - m_size, ey - m_size + 5), (ex - m_size, ey - m_size), (ex - m_size + 5, ey - m_size)
        ], 2)
        pygame.draw.lines(self.screen, color, False, [
            (ex + m_size, ey - m_size + 5), (ex + m_size, ey - m_size), (ex + m_size - 5, ey - m_size)
        ], 2)
        pygame.draw.lines(self.screen, color, False, [
            (ex - m_size, ey + m_size - 5), (ex - m_size, ey + m_size), (ex - m_size + 5, ey + m_size)
        ], 2)
        pygame.draw.lines(self.screen, color, False, [
            (ex + m_size, ey + m_size - 5), (ex + m_size, ey + m_size), (ex + m_size - 5, ey + m_size)
        ], 2)

    def _draw_triangle(self, pos, angle, size, color):
        """指定した角度の三角形を描画"""
        cx, cy = pos
        # 先端
        p1 = (cx + math.cos(angle) * size, cy + math.sin(angle) * size)
        # 後ろ2点（120度ずらす）
        angle2 = angle + math.radians(140)
        angle3 = angle - math.radians(140)
        p2 = (cx + math.cos(angle2) * size, cy + math.sin(angle2) * size)
        p3 = (cx + math.cos(angle3) * size, cy + math.sin(angle3) * size)
        
        pygame.draw.polygon(self.screen, color, [p1, p2, p3])

    # --- バトル共通描画 ---

    def draw_field_guides(self):
        center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
        offset = 40
        h = GAME_PARAMS['SCREEN_HEIGHT']
        for ox in [-offset, offset]:
            lx = center_x + ox
            pygame.draw.line(self.screen, COLORS['GUIDE_LINE'], (lx, 0), (lx, h), 1)

    def draw_home_marker(self, x, y):
        pygame.draw.circle(self.screen, COLORS['HOME_MARKER'], (int(x), int(y + 20)), 22, 2)

    def draw_character_icon(self, icon_x, y, team_color, border_color=None):
        radius = 14
        if border_color:
            pygame.draw.circle(self.screen, border_color, (int(icon_x), int(y + 20)), radius + 4)
        pygame.draw.circle(self.screen, team_color, (int(icon_x), int(y + 20)), radius)

    def draw_hp_bars(self, x, y, hp_data_list):
        for i, data in enumerate(hp_data_list):
            row_y = y + 45 + i * 16
            # ラベル
            self.draw_text(f"{data['label']}:", (x - 45, row_y - 2), (200, 200, 200), 'small')
            # HPバー
            self.draw_bar((x, row_y, 80, 10), data['ratio'], COLORS['HP_BG'], COLORS['HP_GAUGE'])
            # 数値
            self.draw_text(f"{data['current']}/{data['max']}", (x + 85, row_y - 2), COLORS['TEXT'], 'small')

    def draw_target_marker(self, target_eid, char_positions):
        """指定されたターゲットにマーカー(▼)を表示"""
        if target_eid in char_positions:
            pos = char_positions[target_eid]
            # アイコンの少し上に表示
            self.draw_text("▼", (pos['icon_x'], pos['y'] - 6), (255, 255, 0), 'medium', 'center')

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
        
        from battle.utils import calculate_action_menu_layout
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

    def draw_cutin_window(self, attacker_data, target_data, progress):
        """カットインウィンドウを描画"""
        sw, sh = GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']
        
        # 背景オーバーレイ
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        # ウィンドウ枠
        w_w, w_h = 700, 200
        w_x, w_y = (sw - w_w) // 2, (sh - w_h) // 2
        
        self.draw_box((w_x, w_y, w_w, w_h), (20, 20, 40), (100, 200, 255), 3)
        
        # 左右のキャラエリア
        char_box_w = 150
        
        # 攻撃側（左）
        self.draw_box((w_x + 20, w_y + 20, char_box_w, w_h - 40), (40, 40, 60), attacker_data['color'], 2)
        pygame.draw.circle(self.screen, attacker_data['color'], (w_x + 20 + char_box_w // 2, w_y + 80), 40)
        self.draw_text(attacker_data['name'], (w_x + 20 + char_box_w // 2, w_y + 140), font_type='medium', align='center')

        # 防御側（右）
        self.draw_box((w_x + w_w - 20 - char_box_w, w_y + 20, char_box_w, w_h - 40), (40, 40, 60), target_data['color'], 2)
        pygame.draw.circle(self.screen, target_data['color'], (w_x + w_w - 20 - char_box_w // 2, w_y + 80), 40)
        self.draw_text(target_data['name'], (w_x + w_w - 20 - char_box_w // 2, w_y + 140), font_type='medium', align='center')

        # アニメーションオブジェクト（弾など）
        anim_area_start_x = w_x + 20 + char_box_w + 10
        anim_area_end_x = w_x + w_w - 20 - char_box_w - 10
        anim_width = anim_area_end_x - anim_area_start_x
        
        # 弾の現在位置
        bullet_x = anim_area_start_x + anim_width * progress
        bullet_y = w_y + w_h // 2
        
        if progress < 1.0:
            # 弾描画
            pygame.draw.circle(self.screen, (255, 255, 0), (int(bullet_x), int(bullet_y)), 10)
            # 軌跡
            pygame.draw.line(self.screen, (255, 255, 0), (int(anim_area_start_x), int(bullet_y)), (int(bullet_x), int(bullet_y)), 2)