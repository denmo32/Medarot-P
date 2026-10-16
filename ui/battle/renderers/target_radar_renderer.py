"""進行状況に応じたターゲットレーダーを描画する（テーマ色適用）。"""
import math
import pygame

from ui.base.renderer import BaseRenderer
from ui.battle import layout
from features.battle.presentation.view_models import BattleRenderModel
from ui.config import UI_PARAMS


class TargetRadarRenderer(BaseRenderer):
    def __init__(self, screen):
        super().__init__(screen)
        self._last_target_key = None
        self._anim_start_time = 0.0

    def render(self, model: BattleRenderModel):
        radar = model.target_radar
        if radar is None:
            self._last_target_key = None
            return

        screen_size = self.get_screen_size()
        positions = [layout.calculate_robot_position(robot, screen_size) for robot in model.robots]
        if not (0 <= radar.attacker_index < len(positions)
                and 0 <= radar.target_index < len(positions)):
            self._last_target_key = None
            return

        start = positions[radar.attacker_index]
        end = positions[radar.target_index]

        target_key = (radar.attacker_index, radar.target_index)
        now = pygame.time.get_ticks() / 1000.0
        if self._last_target_key != target_key:
            self._last_target_key = target_key
            self._anim_start_time = now

        elapsed = now - self._anim_start_time

        if radar.is_static:
            elapsed = 999.0

        travel_duration = 0.0 if start == end else UI_PARAMS['TARGET_RADAR_TRAVEL_SEC']
        pulse_duration = UI_PARAMS['TARGET_RADAR_PULSE_SEC']
        pulse_count = 2

        if elapsed < travel_duration and travel_duration > 0:
            t = elapsed / travel_duration
            ease_t = 1.0 - (1.0 - t) ** 2
            cx = start[0] + (end[0] - start[0]) * ease_t
            cy = start[1] + (end[1] - start[1]) * ease_t
            scale = 1.0
        else:
            cx, cy = end
            pulse_elapsed = elapsed - travel_duration
            total_pulse_time = pulse_duration * pulse_count
            if pulse_elapsed < total_pulse_time:
                cycle_progress = (pulse_elapsed % pulse_duration) / pulse_duration
                open_ratio = math.sin(cycle_progress * math.pi)
                scale = 1.0 + 0.35 * open_ratio
            else:
                scale = 1.0

        self._draw_radar((cx, cy), scale)

    def _draw_radar(self, center: tuple[float, float], scale: float):
        cx, cy = int(round(center[0])), int(round(center[1]))

        base_size = self.scaled(UI_PARAMS['TARGET_RADAR_SIZE'])
        size = int(round(base_size * scale))
        if size % 2 != 0:
            size += 1
        half = size // 2

        corner_len = min(half, self.scaled(UI_PARAMS['TARGET_RADAR_CORNER_LEN']))
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