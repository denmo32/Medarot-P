"""描画のみを担当するプレゼンテーション層"""

import pygame
import math
from config import COLORS, FONT_NAMES, GAME_PARAMS
from battle.constants import PartType

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

    def draw_robot_icon(self, cx, cy, base_color, part_status, scale=1.0):
        """
        ロボット型アイコンを描画する。
        cx, cy: 基準座標（ロボットの肩付近）
        scale: 拡大縮小率 (1.0 = カットインサイズ)
        """
        # 色決定用ヘルパー
        broken_color = (60, 60, 60)
        def get_col(ptype):
            if part_status is None:
                return base_color
            return base_color if part_status.get(ptype, False) else broken_color

        # 各部位の基本サイズ (scale=1.0)
        limb_w = 16 * scale
        limb_h = 48 * scale
        chest_a = 40 * scale
        chest_h = 40 * scale
        head_r = 16 * scale
        
        # ギャップ等
        leg_gap = 4 * scale
        arm_gap = 4 * scale
        
        # 座標計算 (cx, cyを基準)
        shoulder_y = cy - (16 * scale)
        head_cy = shoulder_y - head_r

        # 胴体（三角形）
        # TopLeft, TopRight, BottomCenter
        chest_points = [
            (cx - chest_a / 2, shoulder_y),
            (cx + chest_a / 2, shoulder_y),
            (cx, shoulder_y + chest_h)
        ]

        legs_y = shoulder_y + chest_h - (8 * scale)
        l_leg_x = cx - leg_gap - limb_w
        r_leg_x = cx + leg_gap

        arms_y = shoulder_y
        l_arm_x = cx - (chest_a / 2) - arm_gap - limb_w
        r_arm_x = cx + (chest_a / 2) + arm_gap

        # 描画実行 (Rectはint型が必要)
        def to_rect(x, y, w, h):
            return (int(x), int(y), int(w), int(h))

        # 脚
        pygame.draw.rect(self.screen, get_col(PartType.LEGS), to_rect(l_leg_x, legs_y, limb_w, limb_h))
        pygame.draw.rect(self.screen, get_col(PartType.LEGS), to_rect(r_leg_x, legs_y, limb_w, limb_h))
        
        # 腕
        pygame.draw.rect(self.screen, get_col(PartType.LEFT_ARM), to_rect(l_arm_x, arms_y, limb_w, limb_h))
        pygame.draw.rect(self.screen, get_col(PartType.RIGHT_ARM), to_rect(r_arm_x, arms_y, limb_w, limb_h))
        
        # 胴体
        pygame.draw.polygon(self.screen, get_col(PartType.HEAD), chest_points)
        
        # 頭
        pygame.draw.circle(self.screen, get_col(PartType.HEAD), (int(cx), int(head_cy)), int(head_r))

    def draw_character_icon(self, icon_x, y, team_color, part_status=None, border_color=None):
        """
        簡易的なロボット型アイコンを描画する。
        part_status: {'head': bool, 'legs': bool, 'right_arm': bool, 'left_arm': bool}
        """
        cx, cy = int(icon_x), int(y + 20)
        
        # 状態枠線（リング）を背面に描画
        if border_color:
            pygame.draw.circle(self.screen, border_color, (cx, cy), 22, 2)

        # 縮小スケールでロボットアイコンを描画
        # ロボットの描画重心(見た目の中心)を cy に合わせるため、基準点(肩)を少し上にずらす
        # 全高96px相当のscale=0.4の場合、高さ約38px。
        # 基準点(肩)から上端まで32px, 下端まで64px (比率1:2)。
        # 重心は基準点より下にあるため、描画基準点を cy より少し上に設定すると丁度よい。
        scale = 0.4
        offset_y = 16 * scale
        
        self.draw_robot_icon(cx, cy - offset_y, team_color, part_status, scale=scale)

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