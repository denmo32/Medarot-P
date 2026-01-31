"""戦闘フィールド上のオブジェクト（機体、ターゲットライン等）の描画"""

import pygame
import math
from ui.config import COLORS, UI_PARAMS, SCREEN_WIDTH, SCREEN_HEIGHT

class FieldRenderer:
    def __init__(self, master):
        self.m = master

    def render(self, snapshot):
        self._draw_guides()
        self._render_characters(snapshot)
        self._render_target_marker(snapshot)
        self._render_target_line(snapshot)

    def _draw_guides(self):
        center_x = SCREEN_WIDTH // 2
        offset, h = 40, SCREEN_HEIGHT
        for ox in [-offset, offset]:
            pygame.draw.line(self.m.screen, COLORS['GUIDE_LINE'], (center_x + ox, 0), (center_x + ox, h), 1)

    def _render_characters(self, snapshot):
        for char in snapshot.characters.values():
            # ホーム位置
            pygame.draw.circle(self.m.screen, COLORS['HOME_MARKER'], (int(char.home_x), int(char.home_y + 20)), 22, 2)
            # 現在位置（アイコン）
            cx, cy = int(char.icon_x), int(char.y + 20)
            if char.border_color:
                pygame.draw.circle(self.m.screen, char.border_color, (cx, cy), 22, 2)
            
            # ロボット外形描画
            self.m.widgets.draw_robot_icon(cx, cy - 6, char.team_color, char.part_status, scale=0.4)
            self.m.draw_text(char.name, (char.x - 20, char.y - 25), font_type='medium')

    def _render_target_marker(self, snapshot):
        if snapshot.target_marker_eid and snapshot.target_marker_eid in snapshot.characters:
            pos = snapshot.characters[snapshot.target_marker_eid]
            self.m.draw_text("▼", (pos.icon_x, pos.y - 6), (255, 255, 0), 'medium', 'center')

    def _render_target_line(self, snapshot):
        if not snapshot.target_line: return
        start_char, end_char, time_offset = snapshot.target_line
        
        sx, sy = start_char.icon_x, start_char.y + 20
        ex, ey = end_char.icon_x, end_char.y + 20
        dx, dy = ex - sx, ey - sy
        dist = math.hypot(dx, dy)
        if dist < 1: return
        
        angle = math.atan2(dy, dx)
        spacing = 30
        move_offset = (time_offset * 100) % spacing
        
        for i in range(int(dist / spacing)):
            d = i * spacing + move_offset
            if d > dist: continue
            px, py = sx + math.cos(angle) * d, sy + math.sin(angle) * d
            self.m.draw_triangle((px, py), angle, 8, (255, 255, 0))