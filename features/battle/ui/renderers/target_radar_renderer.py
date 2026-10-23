"""進行状況に応じたターゲットレーダーを描画する（ステートレスな描画レンダラー）。"""
from typing import Tuple
import pygame

from ui_base.renderer import BaseRenderer
from features.battle.ui import layout
from features.battle.presentation.view_models import BattleRenderModel
from features.battle.ui.config import BATTLE_UI_PARAMS as UI_PARAMS


class TargetRadarRenderer(BaseRenderer):
    def render(self, model: BattleRenderModel):
        radar = model.target_radar
        if radar is None:
            return

        screen_size = self.get_screen_size()
        positions = [layout.calculate_robot_position(robot, screen_size) for robot in model.robots]
        if not (0 <= radar.attacker_index < len(positions)
                and 0 <= radar.target_index < len(positions)):
            return

        start = positions[radar.attacker_index]
        end = positions[radar.target_index]

        p = radar.travel_progress
        cx = start[0] + (end[0] - start[0]) * p
        cy = start[1] + (end[1] - start[1]) * p

        self._draw_radar((cx, cy), radar.scale)

    def _draw_radar(self, center: Tuple[float, float], scale: float):
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