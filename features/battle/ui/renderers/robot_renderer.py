"""ロボットアイコンとフィールド上のマーカーを描画する。"""
import pygame
from ui_base.renderer import BaseRenderer
from ui_base.widgets import MedabotWidgets
from features.battle.ui import layout
from features.battle.presentation.view_models import BattleRenderModel, RobotViewModel
from ui_base.config import resolve_accent_color
from features.battle.ui.config import BATTLE_UI_PARAMS as UI_PARAMS


class RobotRenderer(BaseRenderer):
    def __init__(self, screen):
        super().__init__(screen)
        self.widgets = MedabotWidgets(self)

    def render(self, model: BattleRenderModel):
        screen_size = self.get_screen_size()
        for robot in model.robots:
            self._render_home_marker(robot, screen_size)
            self._render_icon(robot, screen_size)
            self._render_stop_marker(robot, screen_size)
        self._render_preview_target_markers(model, screen_size)

    def _render_icon(self, robot: RobotViewModel, screen_size):
        cx, cy = layout.calculate_robot_position(robot, screen_size)
        accent_color = resolve_accent_color(robot.accent_state, self.theme)
        self.widgets.draw_robot_icon(
            cx, cy, accent_color, robot.part_status, scale=UI_PARAMS.robot_icon_scale
        )

    def _render_home_marker(self, robot: RobotViewModel, screen_size):
        pygame.draw.ellipse(
            self.screen, self.theme.home_marker, layout.calculate_home_marker_rect(robot, screen_size), 1
        )

    def _render_stop_marker(self, robot: RobotViewModel, screen_size):
        if not any(robot.part_stopped.values()):
            return
        icon_scale = UI_PARAMS.robot_icon_scale
        cx, cy = layout.calculate_robot_position(robot, screen_size)
        lightning_size = 20 * icon_scale * self.ui_scale
        part_centers = self.widgets.get_part_centers(cx, cy, scale=icon_scale)

        for part_type, center_pos in part_centers.items():
            if robot.part_stopped.get(part_type, False):
                self.draw_lightning(center_pos, lightning_size, self.theme.stop_effect)

    def _render_preview_target_markers(self, model: BattleRenderModel, screen_size):
        if not model.show_preview_target_markers or model.command_menu is None:
            return
        for index in model.command_menu.preview_target_robot_indices:
            if 0 <= index < len(model.robots):
                self._render_target_marker(model.robots[index], screen_size)

    def _render_target_marker(self, robot: RobotViewModel, screen_size):
        icon_scale = UI_PARAMS.robot_icon_scale
        cx, cy = layout.calculate_robot_position(robot, screen_size)
        bbox = self.widgets.get_icon_bounding_box(cy, scale=icon_scale)
        self.draw_text(
            "▼", (cx, bbox["top_y"] - self.scaled(UI_PARAMS.target_marker_offset)),
            self.theme.target_marker, 'medium', 'center'
        )