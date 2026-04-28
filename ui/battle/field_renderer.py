"""戦闘フィールド上のオブジェクト（機体、ターゲットライン等）の描画"""

import pygame
import math
from ui.config import COLORS, UI_PARAMS

class FieldRenderer:
    def __init__(self, master):
        self.m = master

    def render(self, snapshot):
        self._draw_guides()
        self._render_characters(snapshot)
        self._render_target_marker(snapshot)
        self._render_target_line(snapshot)

    def _draw_guides(self):
        sw, sh = self.m.get_screen_size()
        center_x = sw // 2
        offset = self.m.scale_x(0.05) # 中央からのオフセット5%
        for ox in [-offset, offset]:
            pygame.draw.line(self.m.screen, COLORS['GUIDE_LINE'], (center_x + ox, 0), (center_x + ox, sh), 1)

    def _render_characters(self, snapshot):
        sw, sh = self.m.get_screen_size()
        base_scale = self.m.ui_scale

        for char in snapshot.characters.values():
            # 相対座標から絶対座標へ変換
            home_x, home_y = self.m.to_px(char.home_x_ratio, char.home_y_ratio)
            icon_x, icon_y = self.m.to_px(char.icon_x_ratio, char.y_ratio)
            
            name_x, name_y = self.m.to_px(char.x_ratio, char.y_ratio)

            # リングの基本サイズ
            rx = int(24 * base_scale)
            ry = int(rx * 0.4)  # 扁平率を上げて立体感を出す
            
            # ホーム位置（ガイドとしての楕円）
            home_cy = home_y + int(20 * base_scale)
            home_rect = pygame.Rect(home_x - rx, home_cy - ry, rx * 2, ry * 2)
            pygame.draw.ellipse(self.m.screen, COLORS['HOME_MARKER'], home_rect, 1)
            
            # 現在位置（アイコン）
            cx, cy = icon_x, icon_y + int(20 * base_scale)
            ring_rect = pygame.Rect(cx - rx, cy - ry, rx * 2, ry * 2)
            
            if char.border_color:
                # 1. リングの奥半分を描画
                pygame.draw.arc(self.m.screen, char.border_color, ring_rect, 0, math.pi, 3)
            
            # 2. ロボット外形描画
            # 足元がリングの中央に来るように微調整
            self.m.widgets.draw_robot_icon(cx, cy - int(4 * base_scale), char.team_color, char.part_status, scale=0.4)
            
            if char.border_color:
                # 3. リングの手前半分を描画
                pygame.draw.arc(self.m.screen, char.border_color, ring_rect, math.pi, 2 * math.pi, 3)
            
            self.m.draw_text(char.name, (name_x - int(20*base_scale), name_y - int(25*base_scale)), font_type='medium')

    def _render_target_marker(self, snapshot):
        sw, sh = self.m.get_screen_size()
        base_scale = self.m.ui_scale
        
        if snapshot.target_marker_eid and snapshot.target_marker_eid in snapshot.characters:
            char = snapshot.characters[snapshot.target_marker_eid]
            icon_x, icon_y = self.m.to_px(char.icon_x_ratio, char.y_ratio)
            self.m.draw_text("▼", (icon_x, icon_y - int(6*base_scale)), (255, 255, 0), 'medium', 'center')

    def _render_target_line(self, snapshot):
        if not snapshot.target_line: return
        start_char, end_char, time_offset = snapshot.target_line
        
        base_scale = self.m.ui_scale

        sx, sy = self.m.to_px(start_char.icon_x_ratio, start_char.y_ratio)
        sy += int(20 * base_scale)
        ex, ey = self.m.to_px(end_char.icon_x_ratio, end_char.y_ratio)
        ey += int(20 * base_scale)
        
        dx, dy = ex - sx, ey - sy
        dist = math.hypot(dx, dy)
        if dist < 1: return
        
        angle = math.atan2(dy, dx)
        spacing = 30 * base_scale
        move_offset = (time_offset * 100 * base_scale) % spacing
        
        # 三角形のサイズ
        tri_size = 8 * base_scale

        count = int(dist / spacing)
        for i in range(count):
            d = i * spacing + move_offset
            if d > dist: continue
            px, py = sx + math.cos(angle) * d, sy + math.sin(angle) * d
            self.m.draw_triangle((px, py), angle, tri_size, (255, 255, 0))