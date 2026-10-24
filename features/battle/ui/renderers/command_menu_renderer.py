"""コマンドメニュー（コマンド選択ボタン）を描画する（テーマ色適用）。"""
from typing import Sequence
import pygame

from ui_base.renderer import BaseRenderer
from ui_base.fonts import FontProvider
from features.battle.ui import layout
from features.battle.staging.directives import AwaitPlayerInput
from features.battle.presentation.view_models import CommandMenuItemModel
from features.battle.ui.config import COMMAND_BUTTON_FONT_NAME


class CommandMenuRenderer(BaseRenderer):
    def _init_custom_fonts(self):
        scale = self.ui_scale
        button_font_path = COMMAND_BUTTON_FONT_NAME
        self.fonts['command_button'] = FontProvider.get(button_font_path, 24, scale)
        self.fonts['command_button_focus'] = FontProvider.get(button_font_path, 28, scale)

    def render(self, await_input: AwaitPlayerInput, selected_index: int):
        screen_size = self.get_screen_size()
        rect = layout.calculate_message_window_rect(screen_size)
        pad = layout.calculate_message_padding(screen_size)

        pygame.draw.rect(self.screen, self.theme.cmd_menu_bg, rect)

        self.draw_text(
            f"{await_input.actor.name} ",
            (pad, rect.y + pad),
            color=self.theme.text,
            font_type='medium',
        )

        self._draw_buttons(await_input.menu_items, selected_index, screen_size)

    def _draw_buttons(self, items: Sequence[CommandMenuItemModel], selected_index: int, screen_size):
        layouts = layout.calculate_command_menu_rects(len(items), screen_size)
        action_label_pos = layout.calculate_action_label_position(screen_size)

        for i, item in enumerate(items):
            is_selected = (i == selected_index)
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