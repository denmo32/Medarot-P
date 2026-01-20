import pygame
import math
from config import COLORS, GAME_PARAMS
from battle.constants import PartType
from .base_renderer import BaseRenderer

class FieldRenderer(BaseRenderer):
    """バトルフィールド上のエンティティやガイドの描画を担当"""

    def draw_flow_line(self, start_pos, end_pos, time_offset, color=(255, 255, 0)):
        """攻撃機体からターゲットに向けてフローライン（▶▶▶）を描画する"""
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

    def draw_field_guides(self):
        center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
        offset = 40
        h = GAME_PARAMS['SCREEN_HEIGHT']
        for ox in [-offset, offset]:
            lx = center_x + ox
            pygame.draw.line(self.screen, COLORS['GUIDE_LINE'], (lx, 0), (lx, h), 1)

    def draw_home_marker(self, x, y):
        pygame.draw.circle(self.screen, COLORS['HOME_MARKER'], (int(x), int(y + 20)), 22, 2)

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
        scale = 0.4
        offset_y = 16 * scale
        
        self.draw_robot_icon(cx, cy - offset_y, team_color, part_status, scale=scale)

    def draw_target_marker(self, target_eid, char_positions):
        """行動選択時の予定ターゲットにマーカー(▼)を表示"""
        if target_eid in char_positions:
            pos = char_positions[target_eid]
            # アイコンの少し上に表示
            self.draw_text("▼", (pos['icon_x'], pos['y'] - 6), (255, 255, 0), 'medium', 'center')
