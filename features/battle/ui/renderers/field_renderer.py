"""バトルフィールドの背景とガイドラインを描画する（テーマ色適用）。"""
import pygame

from ui_base.renderer import BaseRenderer
from features.battle.ui import layout


class FieldRenderer(BaseRenderer):
    def render(self):
        screen_size = self.get_screen_size()

        self.draw_box(
            layout.calculate_field_background_rect(screen_size),
            self.theme.field_bg,
            self.theme.panel_border,
            1,
        )

        top_y = layout.calculate_field_top_y(screen_size)
        bottom_y = layout.calculate_field_bottom_y(screen_size)
        for x in layout.calculate_guide_line_xs(screen_size):
            pygame.draw.line(self.screen, self.theme.guide_line, (x, top_y), (x, bottom_y), 1)