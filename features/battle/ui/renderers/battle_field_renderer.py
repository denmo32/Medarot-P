"""フィールド上の動的オブジェクト（ロボットアイコン・マーカー・ターゲットレーダー）を描画する。"""
from typing import Dict, Optional, Sequence, Tuple
import pygame

from domain.constants import ALL_PART_TYPES, TeamType
from ui_base.renderer import BaseRenderer
from ui_base.widgets import MedabotWidgets
from ui_base.config import resolve_accent_color
from features.battle.ui import layout
from features.battle.ui.config import BATTLE_UI_PARAMS as UI_PARAMS
from features.battle.simulation.entities.robot import Robot
from features.battle.staging.target_radar_director import TargetRadarDirector
from features.battle.staging.visual_state import RobotVisualState


class BattleFieldRenderer(BaseRenderer):
    def __init__(self, screen):
        super().__init__(screen)
        self.widgets = MedabotWidgets(self)

    def render(
        self,
        robots: Sequence[Robot],
        visual_states: Dict[Robot, RobotVisualState],
        radar: Optional[TargetRadarDirector] = None,
        preview_target_indices: Sequence[int] = (),
    ):
        screen_size = self.get_screen_size()

        team_counts = {
            TeamType.PLAYER: sum(1 for r in robots if r.team == TeamType.PLAYER),
            TeamType.ENEMY: sum(1 for r in robots if r.team == TeamType.ENEMY),
        }
        team_counters = {TeamType.PLAYER: 0, TeamType.ENEMY: 0}

        robot_positions: list[Tuple[int, int]] = []

        for robot in robots:
            t_cnt = team_counts[robot.team]
            t_idx = team_counters[robot.team]
            team_counters[robot.team] += 1

            pos = layout.calculate_robot_position(robot, screen_size, team_index=t_idx, team_count=t_cnt)
            robot_positions.append(pos)

            vs = visual_states.get(robot)
            self._render_home_marker(robot, t_idx, t_cnt, screen_size)
            if vs:
                self._render_icon(pos, vs)
            self._render_stop_marker(robot, pos)

        for idx in preview_target_indices:
            if 0 <= idx < len(robot_positions):
                self._render_target_marker(robot_positions[idx])

        if radar is not None:
            self._render_radar(radar, robot_positions)

    def _render_home_marker(self, robot: Robot, team_index: int, team_count: int, screen_size):
        rect = layout.calculate_home_marker_rect(robot, screen_size, team_index=team_index, team_count=team_count)
        pygame.draw.ellipse(self.screen, self.theme.home_marker, rect, 1)

    def _render_icon(self, pos: Tuple[int, int], vs: RobotVisualState):
        accent_color = resolve_accent_color(vs.accent_state, self.theme)
        self.widgets.draw_robot_icon(
            pos[0], pos[1], accent_color, vs.parts_break_progress, scale=UI_PARAMS.robot_icon_scale
        )

    def _render_stop_marker(self, robot: Robot, pos: Tuple[int, int]):
        if not any(robot.is_part_stopped(pt) for pt in ALL_PART_TYPES):
            return
        icon_scale = UI_PARAMS.robot_icon_scale
        lightning_size = 20 * icon_scale * self.ui_scale
        part_centers = self.widgets.get_part_centers(pos[0], pos[1], scale=icon_scale)

        for part_type, center_pos in part_centers.items():
            if robot.is_part_stopped(part_type):
                self.draw_lightning(center_pos, lightning_size, self.theme.stop_effect)

    def _render_target_marker(self, pos: Tuple[int, int]):
        icon_scale = UI_PARAMS.robot_icon_scale
        bbox = self.widgets.get_icon_bounding_box(pos[1], scale=icon_scale)
        self.draw_text(
            "▼",
            (pos[0], bbox["top_y"] - self.scaled(UI_PARAMS.target_marker_offset)),
            self.theme.target_marker,
            'medium',
            'center',
        )

    def _render_radar(self, radar: TargetRadarDirector, positions: Sequence[Tuple[int, int]]):
        if not (0 <= radar.attacker_index < len(positions) and 0 <= radar.target_index < len(positions)):
            return

        start = positions[radar.attacker_index]
        end = positions[radar.target_index]
        state = radar.evaluate(is_static=False)
        p = state.travel_progress
        cx = start[0] + (end[0] - start[0]) * p
        cy = start[1] + (end[1] - start[1]) * p

        self._draw_radar_box((cx, cy), state.scale)

    def _draw_radar_box(self, center: Tuple[float, float], scale: float):
        cx, cy = int(round(center[0])), int(round(center[1]))
        base_size = self.scaled(UI_PARAMS.target_radar_size)
        size = int(round(base_size * scale))
        if size % 2 != 0:
            size += 1
        half = size // 2

        corner_len = min(half, self.scaled(UI_PARAMS.target_radar_corner_len))
        thickness = max(2, self.scaled(2))
        color = self.theme.target_radar

        left = cx - half
        right = cx + half
        top = cy - half
        bottom = cy + half

        # ┏
        pygame.draw.rect(self.screen, color, (left, top, corner_len, thickness))
        pygame.draw.rect(self.screen, color, (left, top, thickness, corner_len))
        # ┓
        pygame.draw.rect(self.screen, color, (right - corner_len, top, corner_len, thickness))
        pygame.draw.rect(self.screen, color, (right - thickness, top, thickness, corner_len))
        # ┗
        pygame.draw.rect(self.screen, color, (left, bottom - thickness, corner_len, thickness))
        pygame.draw.rect(self.screen, color, (left, bottom - corner_len, thickness, corner_len))
        # ┛
        pygame.draw.rect(self.screen, color, (right - corner_len, bottom - thickness, corner_len, thickness))
        pygame.draw.rect(self.screen, color, (right - thickness, bottom - corner_len, thickness, corner_len))
