"""メッセージウィンドウと前進マーカーを描画する（テーマ色適用）。"""
import pygame

from ui.base.renderer import BaseRenderer
from ui.battle import layout
from features.battle.presentation.view_models import MessageWindowModel
from ui.config import UI_PARAMS


class MessageRenderer(BaseRenderer):
    def render(self, model: MessageWindowModel):
        screen_size = self.get_screen_size()
        rect = layout.calculate_message_window_rect(screen_size)
        pad = layout.calculate_message_padding(screen_size)

        self.draw_pipe_box(rect, self.theme.msg_bg, self.theme.msg_pipe, self.theme.msg_joint)

        line_h = layout.calculate_log_line_height(screen_size)
        for i, line in enumerate(model.lines):
            self.draw_text(
                line,
                (pad, rect.y + pad + i * line_h),
                color=self.theme.msg_text,
                font_type='medium',
            )

        if model.show_advance_marker:
            self._render_advance_marker(rect, pad)

    def _render_advance_marker(self, rect, pad: int):
        if (pygame.time.get_ticks() // UI_PARAMS['BLINK_INTERVAL_MS']) % 2 != 0:
            return

        marker_size = self.scaled(UI_PARAMS['ADVANCE_MARKER_SIZE'])
        mx = rect.right - pad * 2
        my = rect.bottom - pad * 1.5
        pygame.draw.polygon(self.screen, self.theme.msg_text, [
            (mx - marker_size, my - marker_size),
            (mx + marker_size, my - marker_size),
            (mx, my),
        ])