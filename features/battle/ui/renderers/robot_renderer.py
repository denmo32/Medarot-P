"""ロボットアイコンとフィールド上のマーカーを描画する。"""
import pygame
from domain.constants import ALL_PART_TYPES
from ui_base.renderer import BaseRenderer
from ui_base.widgets import MedabotWidgets
from features.battle.ui import layout
from features.battle.presentation.view_models import BattleRenderModel, RobotRenderContext
from ui_base.config import resolve_accent_color
from features.battle.ui.config import BATTLE_UI_PARAMS as UI_PARAMS


class RobotRenderer(BaseRenderer):
    def __init__(self, screen):
        super().__init__(screen)
        self.widgets = MedabotWidgets(self)

    def render(self, model: BattleRenderModel):
        screen_size = self.get_screen_size()
        for ctx in model.robots:
            self._render_home_marker(ctx, screen_size)
            self._render_icon(ctx, screen_size)
            self._render_stop_marker(ctx, screen_size)
        self._render_preview_target_markers(model, screen_size)

    def _render_icon(self, ctx: RobotRenderContext, screen_size):
        cx, cy = layout.calculate_robot_position(ctx, screen_size)
        accent_color = resolve_accent_color(ctx.accent_state, self.theme)
        self.widgets.draw_robot_icon(
            cx, cy, accent_color, ctx.visual_state.parts_break_progress, scale=UI_PARAMS.robot_icon_scale
        )

    def _render_home_marker(self, ctx: RobotRenderContext, screen_size):
        pygame.draw.ellipse(
            self.screen, self.theme.home_marker, layout.calculate_home_marker_rect(ctx, screen_size), 1
        )

    def _render_stop_marker(self, ctx: RobotRenderContext, screen_size):
        if not any(ctx.robot.is_part_stopped(pt) for pt in ALL_PART_TYPES):
            return
        icon_scale = UI_PARAMS.robot_icon_scale
        cx, cy = layout.calculate_robot_position(ctx, screen_size)
        lightning_size = 20 * icon_scale * self.ui_scale
        part_centers = self.widgets.get_part_centers(cx, cy, scale=icon_scale)

        for part_type, center_pos in part_centers.items():
            if ctx.robot.is_part_stopped(part_type):
                self.draw_lightning(center_pos, lightning_size, self.theme.stop_effect)

    def _render_preview_target_markers(self, model: BattleRenderModel, screen_size):
        if not model.command_menu or not model.command_menu.preview_target_robot_indices:
            return
        for index in model.command_menu.preview_target_robot_indices:
            if 0 <= index < len(model.robots):
                self._render_target_marker(model.robots[index], screen_size)

    def _render_target_marker(self, ctx: RobotRenderContext, screen_size):
        icon_scale = UI_PARAMS.robot_icon_scale
        cx, cy = layout.calculate_robot_position(ctx, screen_size)
        bbox = self.widgets.get_icon_bounding_box(cy, scale=icon_scale)
        self.draw_text(
            "▼", (cx, bbox["top_y"] - self.scaled(UI_PARAMS.target_marker_offset)),
            self.theme.target_marker, 'medium', 'center'
        )