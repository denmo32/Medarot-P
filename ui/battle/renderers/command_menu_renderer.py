"""コマンドメニュー（コマンド選択ボタン）を描画する（テーマ色適用）。"""
import pygame

from ui.base.renderer import BaseRenderer
from ui.battle import layout
from features.battle.presentation.view_models import CommandMenuModel


class CommandMenuRenderer(BaseRenderer):
    def render(self, model: CommandMenuModel):
        screen_size = self.get_screen_size()
        rect = layout.calculate_message_window_rect(screen_size)
        pad = layout.calculate_message_padding(screen_size)

        pygame.draw.rect(self.screen, self.theme.cmd_menu_bg, rect)

        self.draw_text(
            f"{model.actor_name} ",
            (pad, rect.y + pad),
            color=self.theme.text,
            font_type='medium',
        )

        self._draw_buttons(model, screen_size)

    def _draw_buttons(self, model: CommandMenuModel, screen_size):
        layouts = layout.calculate_command_menu_rects(len(model.items), screen_size)
        action_label_pos = layout.calculate_action_label_position(screen_size)

        for i, item in enumerate(model.items):
            is_selected = (i == model.selected_index)
            rect = layouts[i]

            bg = self.theme.cmd_btn_focus_bg if is_selected else self.theme.cmd_btn_normal_bg
            if not item.visual_enabled:
                bg = self.theme.button_disabled_bg

            self.draw_box(rect, bg, self.theme.button_border, 2)
            self.draw_text(item.label, rect.center, self.theme.text, 'command_button', 'center')

            if is_selected and item.action_label:
                self.draw_text(
                    f"{item.action_label}",
                    action_label_pos,
                    self.theme.action_label_text,
                    'medium',
                )