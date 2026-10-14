"""メダロット固有の共通UIコンポーネント"""
import pygame
from domain.constants import PartType
from ui.base.renderer import BaseRenderer


class MedabotWidgets:
    """ロボットアイコンやHPゲージなど、複数の画面で利用するパーツ描画"""
    def __init__(self, renderer: BaseRenderer):
        self.renderer = renderer

    def _calc_dimensions(self, scale: float = 1.0) -> dict:
        s = scale * self.renderer.ui_scale
        limb_w = max(2, int(round(16 * s)))
        limb_h = max(4, int(round(48 * s)))
        gap = max(1, int(round(4 * s)))
        chest_w = max(4, int(round(40 * s)))
        half_chest_w = chest_w // 2
        chest_h = max(4, int(round(40 * s)))
        head_r = max(2, int(round(16 * s)))
        leg_offset_y = chest_h - max(1, int(round(8 * s)))

        return {
            "limb_w": limb_w,
            "limb_h": limb_h,
            "gap": gap,
            "chest_w": chest_w,
            "half_chest_w": half_chest_w,
            "chest_h": chest_h,
            "head_r": head_r,
            "leg_offset_y": leg_offset_y,
        }

    def get_icon_bounding_box(self, cy: float, scale: float = 1.0) -> dict:
        d = self._calc_dimensions(scale)
        top_y = -d["head_r"] * 2
        bottom_y = d["leg_offset_y"] + d["limb_h"]
        center_offset_y = -(top_y + bottom_y) / 2.0

        return {
            "top_y": cy + center_offset_y + top_y,
            "bottom_y": cy + center_offset_y + bottom_y,
            "center_y": cy,
            "shoulder_y": cy + center_offset_y,
        }

    def get_part_centers(self, cx: float, cy: float, scale: float = 1.0) -> dict[PartType, tuple[float, float]]:
        d = self._calc_dimensions(scale)
        bbox = self.get_icon_bounding_box(cy, scale)
        sy = bbox["shoulder_y"]
        cx = int(round(cx))

        arm_offset_x = d["half_chest_w"] + d["gap"] + (d["limb_w"] / 2.0)
        leg_cy = sy + d["leg_offset_y"] + (d["limb_h"] / 2.0)
        arm_cy = sy + (d["limb_h"] / 2.0)

        return {
            PartType.HEAD: (cx, sy - d["head_r"]),
            PartType.RIGHT_ARM: (cx - arm_offset_x, arm_cy),
            PartType.LEFT_ARM: (cx + arm_offset_x, arm_cy),
            PartType.LEGS: (cx, leg_cy),
        }

    def draw_robot_icon(self, cx, cy, base_color, part_status, scale=1.0):
        d = self._calc_dimensions(scale)
        bbox = self.get_icon_bounding_box(cy, scale)
        shoulder_y = int(round(bbox["shoulder_y"]))
        cx = int(round(cx))

        broken_color = self.renderer.theme.icon_stopped

        def get_col(ptype):
            if part_status is None:
                return base_color
            progress = max(0.0, min(1.0, float(part_status.get(ptype, 0.0))))

            if progress <= 0.0:
                return base_color
            if progress >= 1.0:
                return broken_color

            return (
                int(round(base_color[0] + (broken_color[0] - base_color[0]) * progress)),
                int(round(base_color[1] + (broken_color[1] - base_color[1]) * progress)),
                int(round(base_color[2] + (broken_color[2] - base_color[2]) * progress)),
            )

        self._draw_legs(cx, shoulder_y, get_col(PartType.LEGS), d)
        self._draw_arms(cx, shoulder_y, get_col(PartType.RIGHT_ARM), get_col(PartType.LEFT_ARM), d)
        self._draw_torso(cx, shoulder_y, get_col(PartType.HEAD), d)
        self._draw_head(cx, shoulder_y, get_col(PartType.HEAD), d)

    def _draw_legs(self, cx, sy, color, d):
        limb_w, limb_h = d["limb_w"], d["limb_h"]
        gap, y = d["gap"], sy + d["leg_offset_y"]
        pygame.draw.rect(self.renderer.screen, color, (cx - gap - limb_w, y, limb_w, limb_h))
        pygame.draw.rect(self.renderer.screen, color, (cx + gap, y, limb_w, limb_h))

    def _draw_arms(self, cx, sy, r_color, l_color, d):
        limb_w, limb_h = d["limb_w"], d["limb_h"]
        gap, half_w = d["gap"], d["half_chest_w"]
        lx = cx - half_w - gap - limb_w
        rx = cx + half_w + gap
        pygame.draw.rect(self.renderer.screen, r_color, (lx, sy, limb_w, limb_h))
        pygame.draw.rect(self.renderer.screen, l_color, (rx, sy, limb_w, limb_h))

    def _draw_torso(self, cx, sy, color, d):
        half_w, h = d["half_chest_w"], d["chest_h"]
        points = [(cx - half_w, sy), (cx + half_w, sy), (cx, sy + h)]
        pygame.draw.polygon(self.renderer.screen, color, points)

    def _draw_head(self, cx, sy, color, d):
        r = d["head_r"]
        pygame.draw.circle(self.renderer.screen, color, (cx, sy - r), r)