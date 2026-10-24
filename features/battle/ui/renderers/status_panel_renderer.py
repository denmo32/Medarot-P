"""画面上部の各機体ステータスを描画するレンダラー（Robot と RobotVisualState を直接解釈）。"""
import pygame
from typing import Dict, List, Optional, Sequence, Tuple

from domain.constants import ALL_PART_TYPES, EffectType, TeamType
from domain.models import StatusEffect
from ui_base.renderer import BaseRenderer
from ui_base.config import resolve_accent_color
from features.battle.ui import layout
from features.battle.simulation.entities.robot import Robot
from features.battle.staging.cutin_director import CutinDirector
from features.battle.staging.visual_state import RobotVisualState


class StatusPanelRenderer(BaseRenderer):
    def render(
        self,
        robots: Sequence[Robot],
        visual_states: Dict[Robot, RobotVisualState],
        cutin: Optional[CutinDirector] = None,
    ):
        screen_size = self.get_screen_size()
        panel_layout = layout.calculate_top_status_layout(screen_size)
        dim_active = cutin is not None

        player_robots = [r for r in robots if r.team == TeamType.PLAYER]
        enemy_robots = [r for r in robots if r.team == TeamType.ENEMY]

        self.draw_box(panel_layout['left_panel_rect'], self.theme.status_panel_bg, self.theme.status_panel_border, 1)
        for robot, card_rect in zip(player_robots, panel_layout['left_card_rects']):
            vs = visual_states.get(robot)
            if vs:
                is_active = cutin.is_combatant(robot) if cutin else False
                self._render_robot_card(robot, vs, card_rect, dim_active, is_active)

        self.draw_box(panel_layout['right_panel_rect'], self.theme.status_panel_bg, self.theme.status_panel_border, 1)
        for robot, card_rect in zip(enemy_robots, panel_layout['right_card_rects']):
            vs = visual_states.get(robot)
            if vs:
                is_active = cutin.is_combatant(robot) if cutin else False
                self._render_robot_card(robot, vs, card_rect, dim_active, is_active)

    def _render_robot_card(
        self,
        robot: Robot,
        vs: RobotVisualState,
        rect: pygame.Rect,
        dim_active: bool,
        is_combat_active: bool,
    ):
        is_alive = vs.is_visually_alive

        bg_col = self.theme.status_card_bg if is_alive else self.theme.status_card_dead_bg
        self.draw_box(rect, bg_col, self.theme.status_card_border, 1)

        accent_color = resolve_accent_color(vs.accent_state, self.theme)
        bar_h = self.scaled(6)
        pygame.draw.rect(self.screen, accent_color, (rect.x + 1, rect.y + 1, rect.width - 2, bar_h))

        self.screen.set_clip(rect)
        pad = self.scaled(4)
        content_y = rect.y + 1 + bar_h + pad

        name_col = self.theme.text if is_alive else self.theme.status_card_dead_text
        display_name = f"{robot.name}[LEADER]" if robot.is_leader else robot.name
        self.draw_text(display_name, (rect.x + pad, content_y), name_col, 'small')

        second_y = content_y + self.scaled(16)
        badges = self._extract_badges(robot.active_effects)
        target_text = self._extract_target_text(robot)

        if badges:
            badge_x = rect.x + pad
            badge_limit = rect.right - pad
            for text, bg_c, text_c in badges:
                badge_surf = self.fonts['tiny'].render(text, True, text_c)
                bw = badge_surf.get_width() + self.scaled(4)
                bh = badge_surf.get_height() + self.scaled(2)
                if badge_x + bw > badge_limit:
                    break
                pygame.draw.rect(self.screen, bg_c, (badge_x, second_y, bw, bh))
                self.screen.blit(badge_surf, (badge_x + self.scaled(2), second_y + self.scaled(1)))
                badge_x += bw + self.scaled(3)
        elif target_text:
            self.draw_text(target_text, (rect.x + pad, second_y), self.theme.status_target_text, 'tiny')

        divider_y = content_y + self.scaled(31)
        pygame.draw.line(self.screen, self.theme.status_card_border, (rect.x + pad, divider_y), (rect.right - pad, divider_y), 1)

        avail_w = rect.width - pad * 2
        self._render_parts_hp_list(robot, vs, rect.x + pad, divider_y + self.scaled(3), avail_w, is_alive)
        self.screen.set_clip(None)

        if dim_active and not is_combat_active:
            dim = pygame.Surface(rect.size, pygame.SRCALPHA)
            dim.fill(self.theme.status_card_dim)
            self.screen.blit(dim, rect.topleft)

    def _render_parts_hp_list(
        self,
        robot: Robot,
        vs: RobotVisualState,
        start_x: int,
        start_y: int,
        avail_w: int,
        is_alive: bool,
    ):
        row_h = self.scaled(18)
        right_x = start_x + avail_w
        label_w = self.scaled(38)
        bar_h = self.scaled(8)
        num_w = self.scaled(56)

        for i, pt in enumerate(ALL_PART_TYPES):
            part = robot.get_part(pt)
            if not part:
                continue

            ry = start_y + i * row_h
            display_hp = float(vs.parts_display_hp.get(pt, part.hp))
            max_hp = max(1, part.max_hp)
            is_part_alive = display_hp > 0
            is_stopped = robot.is_part_stopped(pt)

            lbl_col = self.theme.status_part_label if is_part_alive else self.theme.hp_broken_text
            self.draw_text(pt.label, (start_x, ry), lbl_col, 'small')

            if is_stopped:
                self.draw_text("⚡", (start_x + label_w - self.scaled(10), ry - self.scaled(1)), self.theme.stop_effect, 'tiny')

            bar_x = start_x + label_w
            bar_w = (right_x - num_w) - bar_x
            ratio = max(0.0, min(1.0, display_hp / max_hp)) if is_part_alive else 0.0

            if not is_part_alive:
                bar_col = self.theme.hp_danger
            elif ratio > 0.5:
                bar_col = self.theme.hp_safe
            elif ratio > 0.25:
                bar_col = self.theme.hp_warn
            else:
                bar_col = self.theme.hp_danger

            self.draw_bar((bar_x, ry + self.scaled(5), bar_w, bar_h), ratio, self.theme.hp_bg, bar_col, self.theme.hp_border)

            num_col = self.theme.status_part_num if is_part_alive else self.theme.hp_broken_text
            self.draw_text(f"{int(display_hp)}/{max_hp}", (right_x, ry), num_col, 'small', 'right')

    def _extract_badges(self, effects: Tuple[StatusEffect, ...]) -> List[Tuple[str, Tuple[int, int, int], Tuple[int, int, int]]]:
        badges = []
        for eff in effects:
            if eff.type == EffectType.STOP:
                label = f" {eff.part_type.label}" if eff.part_type else ""
                badges.append((f"停止{label} {eff.duration:.1f}s", self.theme.badge_stop_bg, self.theme.badge_stop_text))
            elif eff.type == EffectType.BLOCK:
                badges.append(("護衛 (BLOCK)", self.theme.badge_stance_bg, self.theme.text))
            elif eff.type == EffectType.PROTECT:
                badges.append(("自衛 (PROTECT)", self.theme.badge_stance_bg, self.theme.text))
            elif eff.type == EffectType.SUCCESS_UP:
                charges = eff.charges if eff.charges is not None else 1
                badges.append((f"命中+{eff.magnitude} ({charges}回)", self.theme.badge_buff_bg, self.theme.text))
        return badges

    def _extract_target_text(self, robot: Robot) -> Optional[str]:
        if not robot.is_charging:
            return None
        cmd = robot.current_part_command
        part = robot.current_part
        if not cmd or not part:
            return None

        if cmd.target_robot:
            text = cmd.target_robot.name
            if cmd.target_part:
                text += f" [{cmd.target_part.label}]"
            return f"└> {text}"

        if not part.locks_target:
            return "└> 直前選定"
        return None