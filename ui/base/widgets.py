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
        cx, cy: 基準座標（ロボットの肩付近）
        scale: 拡大縮小率 (1.0 = カットインサイズ)
        """
        screen = self.renderer.screen
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
        pygame.draw.rect(screen, get_col(PartType.LEGS), to_rect(l_leg_x, legs_y, limb_w, limb_h))
        pygame.draw.rect(screen, get_col(PartType.LEGS), to_rect(r_leg_x, legs_y, limb_w, limb_h))
        
        # 腕
        # 正面向き（対面）にするため、画面左側(l_arm_x)に右腕、画面右側(r_arm_x)に左腕を描画
        pygame.draw.rect(screen, get_col(PartType.RIGHT_ARM), to_rect(l_arm_x, arms_y, limb_w, limb_h))
        pygame.draw.rect(screen, get_col(PartType.LEFT_ARM), to_rect(r_arm_x, arms_y, limb_w, limb_h))
        
        # 胴体
        pygame.draw.polygon(screen, get_col(PartType.HEAD), chest_points)
        
        # 頭
        pygame.draw.circle(screen, get_col(PartType.HEAD), (int(cx), int(head_cy)), int(head_r))