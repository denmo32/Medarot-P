"""
メダロット固有の共通UIコンポーネント
BaseRendererを利用して、ドメイン特有の図形を描画する。
"""

import pygame
from config import COLORS
from battle.constants import PartType
from ui.base.renderer import BaseRenderer

class MedabotWidgets:
    """ロボットアイコンやHPゲージなど、複数の画面で利用するパーツ描画"""
    
    def __init__(self, renderer: BaseRenderer):
        self.renderer = renderer

    def draw_hp_bars(self, x, y, hp_data_list):
        """HPゲージのセットを描画"""
        for i, data in enumerate(hp_data_list):
            row_y = y + 45 + i * 16
            # ラベル
            self.renderer.draw_text(f"{data['label']}:", (x - 45, row_y - 2), (200, 200, 200), 'small')
            # HPバー
            self.renderer.draw_bar((x, row_y, 80, 10), data['ratio'], COLORS['HP_BG'], COLORS['HP_GAUGE'])
            # 数値
            self.renderer.draw_text(f"{data['current']}/{data['max']}", (x + 85, row_y - 2), COLORS['TEXT'], 'small')

    def draw_robot_icon(self, cx, cy, base_color, part_status, scale=1.0):
        """
        ロボット型アイコンを描画する。
        部位ごとのメソッドに分割して描画を行う。
        """
        # 描画用パラメータの計算
        broken_color = (60, 60, 60)
        def get_col(ptype):
            if part_status is None: return base_color
            return base_color if part_status.get(ptype, False) else broken_color

        # サイズ計算
        s = scale
        shoulder_y = cy - (16 * s)
        
        # 1. 脚
        self._draw_legs(cx, shoulder_y, get_col(PartType.LEGS), s)
        # 2. 腕
        self._draw_arms(cx, shoulder_y, get_col(PartType.RIGHT_ARM), get_col(PartType.LEFT_ARM), s)
        # 3. 胴体
        self._draw_torso(cx, shoulder_y, get_col(PartType.HEAD), s)
        # 4. 頭部
        self._draw_head(cx, shoulder_y, get_col(PartType.HEAD), s)

    def _draw_legs(self, cx, sy, color, s):
        limb_w, limb_h = 16 * s, 48 * s
        gap, chest_h = 4 * s, 40 * s
        y = sy + chest_h - (8 * s)
        # 左右の脚
        pygame.draw.rect(self.renderer.screen, color, (int(cx - gap - limb_w), int(y), int(limb_w), int(limb_h)))
        pygame.draw.rect(self.renderer.screen, color, (int(cx + gap), int(y), int(limb_w), int(limb_h)))

    def _draw_arms(self, cx, sy, r_color, l_color, s):
        limb_w, limb_h = 16 * s, 48 * s
        gap, chest_a = 4 * s, 40 * s
        # 正面向き（画面左に右腕、右に左腕）
        lx = cx - (chest_a / 2) - gap - limb_w
        rx = cx + (chest_a / 2) + gap
        pygame.draw.rect(self.renderer.screen, r_color, (int(lx), int(sy), int(limb_w), int(limb_h)))
        pygame.draw.rect(self.renderer.screen, l_color, (int(rx), int(sy), int(limb_w), int(limb_h)))

    def _draw_torso(self, cx, sy, color, s):
        a, h = 40 * s, 40 * s
        points = [(cx - a/2, sy), (cx + a/2, sy), (cx, sy + h)]
        pygame.draw.polygon(self.renderer.screen, color, points)

    def _draw_head(self, cx, sy, color, s):
        r = 16 * s
        pygame.draw.circle(self.renderer.screen, color, (int(cx), int(sy - r)), int(r))