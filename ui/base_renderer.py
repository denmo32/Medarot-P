import pygame
from config import COLORS, FONT_NAMES
from battle.constants import PartType

class BaseRenderer:
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

    def _draw_triangle(self, pos, angle, size, color):
        """指定した角度の三角形を描画（サブクラス用ユーティリティ）"""
        import math
        cx, cy = pos
        # 先端
        p1 = (cx + math.cos(angle) * size, cy + math.sin(angle) * size)
        # 後ろ2点（120度ずらす）
        angle2 = angle + math.radians(140)
        angle3 = angle - math.radians(140)
        p2 = (cx + math.cos(angle2) * size, cy + math.sin(angle2) * size)
        p3 = (cx + math.cos(angle3) * size, cy + math.sin(angle3) * size)
        
        pygame.draw.polygon(self.screen, color, [p1, p2, p3])

    # --- 共通UIコンポーネント ---

    def draw_hp_bars(self, x, y, hp_data_list):
        for i, data in enumerate(hp_data_list):
            row_y = y + 45 + i * 16
            # ラベル
            self.draw_text(f"{data['label']}:", (x - 45, row_y - 2), (200, 200, 200), 'small')
            # HPバー
            self.draw_bar((x, row_y, 80, 10), data['ratio'], COLORS['HP_BG'], COLORS['HP_GAUGE'])
            # 数値
            self.draw_text(f"{data['current']}/{data['max']}", (x + 85, row_y - 2), COLORS['TEXT'], 'small')

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
        # 正面向き（対面）にするため、画面左側(l_arm_x)に右腕、画面右側(r_arm_x)に左腕を描画
        pygame.draw.rect(self.screen, get_col(PartType.RIGHT_ARM), to_rect(l_arm_x, arms_y, limb_w, limb_h))
        pygame.draw.rect(self.screen, get_col(PartType.LEFT_ARM), to_rect(r_arm_x, arms_y, limb_w, limb_h))
        
        # 胴体
        pygame.draw.polygon(self.screen, get_col(PartType.HEAD), chest_points)
        
        # 頭
        pygame.draw.circle(self.screen, get_col(PartType.HEAD), (int(cx), int(head_cy)), int(head_r))
