"""画面上部の各機体ステータスを描画するレンダラー（論理状態からTheme色解決）。"""
import pygame
from typing import List, Tuple

from domain.constants import BadgeKind
from ui.base.renderer import BaseRenderer
from ui.battle import layout
from features.battle.presentation.view_models import (
    TopStatusPanelModel,
    RobotStatusCardModel,
    PartMiniHpModel,
)
from ui.config import Theme, resolve_accent_color


def resolve_badge_colors(kind: BadgeKind, theme: Theme) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    if kind == BadgeKind.STOP:
        return theme.badge_stop_bg, theme.badge_stop_text
    if kind == BadgeKind.BLOCK:
        return theme.badge_stance_bg, theme.text
    if kind == BadgeKind.PROTECT:
        return theme.badge_stance_bg, theme.text
    if kind == BadgeKind.SUCCESS_UP:
        return theme.badge_buff_bg, theme.text
    return theme.panel_bg, theme.text


class StatusPanelRenderer(BaseRenderer):
    def render(self, model: TopStatusPanelModel):
        screen_size = self.get_screen_size()
        panel_layout = layout.calculate_top_status_layout(screen_size)
        all_cards = list(model.player_cards) + list(model.enemy_cards)
        dim_active = any(card.is_combat_active for card in all_cards)

        self.draw_box(panel_layout['left_panel_rect'], self.theme.status_panel_bg, self.theme.status_panel_border, 1)
        for card_model, card_rect in zip(model.player_cards, panel_layout['left_card_rects']):
            self._render_robot_card(card_model, card_rect, dim_active)

        self.draw_box(panel_layout['right_panel_rect'], self.theme.status_panel_bg, self.theme.status_panel_border, 1)
        for card_model, card_rect in zip(model.enemy_cards, panel_layout['right_card_rects']):
            self._render_robot_card(card_model, card_rect, dim_active)

    def _render_robot_card(self, card: RobotStatusCardModel, rect: pygame.Rect, dim_active: bool = False):
        bg_col = self.theme.status_card_bg if card.is_alive else self.theme.status_card_dead_bg
        self.draw_box(rect, bg_col, self.theme.status_card_border, 1)

        accent_color = resolve_accent_color(card.accent_state, self.theme)
        bar_h = self.scaled(6)
        pygame.draw.rect(self.screen, accent_color, (rect.x + 1, rect.y + 1, rect.width - 2, bar_h))

        self.screen.set_clip(rect)
        pad = self.scaled(4)
        content_y = rect.y + 1 + bar_h + pad

        name_col = self.theme.text if card.is_alive else self.theme.status_card_dead_text
        self.draw_text(card.name, (rect.x + pad, content_y), name_col, 'small')

        second_y = content_y + self.scaled(16)
        if card.badges:
            badge_x = rect.x + pad
            badge_limit = rect.right - pad
            for badge in card.badges:
                bg_c, text_c = resolve_badge_colors(badge.badge_kind, self.theme)
                badge_surf = self.fonts['tiny'].render(badge.text, True, text_c)
                bw = badge_surf.get_width() + self.scaled(4)
                bh = badge_surf.get_height() + self.scaled(2)
                if badge_x + bw > badge_limit:
                    break
                pygame.draw.rect(self.screen, bg_c, (badge_x, second_y, bw, bh))
                self.screen.blit(badge_surf, (badge_x + self.scaled(2), second_y + self.scaled(1)))
                badge_x += bw + self.scaled(3)
        elif card.target_text:
            self.draw_text(card.target_text, (rect.x + pad, second_y), self.theme.status_target_text, 'tiny')

        divider_y = content_y + self.scaled(31)
        pygame.draw.line(self.screen, self.theme.status_card_border, (rect.x + pad, divider_y), (rect.right - pad, divider_y), 1)

        avail_w = rect.width - pad * 2
        self._render_parts_hp_list(card.parts_hp, rect.x + pad, divider_y + self.scaled(3), avail_w, card.is_alive)
        self.screen.set_clip(None)

        if dim_active and not card.is_combat_active:
            dim = pygame.Surface(rect.size, pygame.SRCALPHA)
            dim.fill(self.theme.status_card_dim)
            self.screen.blit(dim, rect.topleft)

    def _render_parts_hp_list(self, parts_hp: List[PartMiniHpModel], start_x: int, start_y: int, avail_w: int, is_alive: bool):
        row_h = self.scaled(18)
        right_x = start_x + avail_w
        label_w = self.scaled(38)

        for i, p in enumerate(parts_hp):
            ry = start_y + i * row_h
            is_part_alive = not p.is_broken
            lbl_col = self.theme.status_part_label if is_part_alive else self.theme.hp_broken_text

            self.draw_text(p.label or "", (start_x, ry), lbl_col, 'small')

            if p.is_stopped:
                self.draw_text("⚡", (start_x + label_w - self.scaled(10), ry - self.scaled(1)), self.theme.stop_effect, 'tiny')

            bar_x = start_x + label_w
            num_w = self.scaled(56)
            bar_w = (right_x - num_w) - bar_x
            bar_h = self.scaled(8)
            bar_ratio = 0.0 if not is_part_alive else p.ratio

            if not is_part_alive or p.current_hp <= 0: bar_col = self.theme.hp_danger
            elif p.ratio > 0.5: bar_col = self.theme.hp_safe
            elif p.ratio > 0.25: bar_col = self.theme.hp_warn
            else: bar_col = self.theme.hp_danger

            self.draw_bar((bar_x, ry + self.scaled(5), bar_w, bar_h), bar_ratio, self.theme.hp_bg, bar_col, self.theme.hp_border)

            num_col = self.theme.status_part_num if is_part_alive else self.theme.hp_broken_text
            self.draw_text(f"{p.current_hp}/{p.max_hp}", (right_x, ry), num_col, 'small', 'right')