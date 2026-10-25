"""バトル画面の描画オーケストレーション（ファサード）。"""
from typing import List, Optional, Tuple
import pygame

from domain.constants import TeamType
from ui_base.renderer import BaseRenderer
from features.battle.ui import layout
from features.battle.ui.config import BATTLE_UI_PARAMS as UI_PARAMS
from features.battle.staging.director import BattleDirector
from features.battle.ui.renderers.battle_field_renderer import BattleFieldRenderer
from features.battle.ui.renderers.command_menu_renderer import CommandMenuRenderer
from features.battle.ui.renderers.cutin_renderer import CutinRenderer
from features.battle.ui.renderers.status_panel_renderer import StatusPanelRenderer

OPENING_POPUP_TEXT = "ロボトルファイト！"
WINNER_TEXTS = {
    TeamType.PLAYER: "WIN！",
    TeamType.ENEMY: "LOSE...",
}


class BattleRenderer(BaseRenderer):
    """バトル画面の描画順を制御するファサード"""

    def __init__(self, screen):
        super().__init__(screen)

        self.status_panel = StatusPanelRenderer(screen)
        self.field_objects = BattleFieldRenderer(screen)
        self.command_menu = CommandMenuRenderer(screen)
        self.cutin = CutinRenderer(screen)

    def render(self, director: BattleDirector, selected_command_index: int = 0):
        """Director および Manager から直接 1 フレーム分の描画を行う"""
        self.clear()
        manager = director.manager
        screen_size = self.get_screen_size()

        # 1. 画面上部ステータスパネル
        self.status_panel.render(manager.robots, director.visual_states, director.cutin)

        # 2. フィールド背景とガイドライン
        self._render_field(screen_size)

        # 3. フィールド上のオブジェクト（機体アイコン、マーカー、レーダー）
        preview_indices: list[int] = []
        input_await = director.current_player_input_await
        if input_await and 0 <= selected_command_index < len(input_await.menu_items):
            item = input_await.menu_items[selected_command_index]
            if item.preview_target_robot_index is not None:
                preview_indices.append(item.preview_target_robot_index)

        self.field_objects.render(
            manager.robots,
            director.visual_states,
            radar=director.radar,
            preview_target_indices=preview_indices,
        )

        # 4. コマンドメニュー または メッセージウィンドウ
        if input_await:
            self.command_menu.render(input_await, selected_command_index)
        else:
            show_advance = director.can_user_confirm and not director.is_hp_animating()
            self._render_message_window(director.active_messages, show_advance, screen_size)

        # 5. カットイン演出（アクティブ時）
        if director.cutin:
            cutin_state = director.cutin.get_render_state(director.visual_states)
            self.cutin.render(cutin_state)

        # 6. オーバーレイ（開幕演出・勝敗表示）
        if director.opening_popup_visible:
            self._render_opening_popup(screen_size)
        elif director.is_game_over and manager.winner is not None:
            self._render_game_over(manager.winner, screen_size)

        self.present()

    def _render_field(self, screen_size: Tuple[int, int]):
        self.draw_box(
            layout.calculate_field_background_rect(screen_size),
            self.theme.field_bg,
            self.theme.panel_border,
            1,
        )
        top_y = layout.calculate_field_top_y(screen_size)
        bottom_y = layout.calculate_field_bottom_y(screen_size)
        for x in layout.calculate_guide_line_xs(screen_size):
            pygame.draw.line(self.screen, self.theme.guide_line, (x, top_y), (x, bottom_y), 1)

    def _render_message_window(self, messages: List[str], show_advance: bool, screen_size: Tuple[int, int]):
        rect = layout.calculate_message_window_rect(screen_size)
        pad = layout.calculate_message_padding(screen_size)

        self.draw_pipe_box(rect, self.theme.msg_bg, self.theme.msg_pipe, self.theme.msg_joint)

        line_h = layout.calculate_log_line_height(screen_size)
        max_lines = max(1, (rect.height - pad * 2) // max(1, line_h))
        visible_lines = messages[-max_lines:]
        for i, line in enumerate(visible_lines):
            self.draw_text(
                line,
                (pad, rect.y + pad + i * line_h),
                color=self.theme.msg_text,
                font_type='medium',
            )

        if show_advance:
            if (pygame.time.get_ticks() // UI_PARAMS.blink_interval_ms) % 2 == 0:
                marker_size = self.scaled(UI_PARAMS.advance_marker_size)
                mx = rect.right - pad * 2
                my = rect.bottom - pad * 1.5
                pygame.draw.polygon(self.screen, self.theme.msg_text, [
                    (mx - marker_size, my - marker_size),
                    (mx + marker_size, my - marker_size),
                    (mx, my),
                ])

    def _render_opening_popup(self, screen_size: Tuple[int, int]):
        sw, sh = screen_size
        self.draw_text_with_outline(
            OPENING_POPUP_TEXT, sw // 2, sh // 2, self.theme.text, 'notice', 'center',
        )

    def _render_game_over(self, winner: TeamType, screen_size: Tuple[int, int]):
        sw, sh = screen_size
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill(self.theme.notice_bg)
        self.screen.blit(overlay, (0, 0))

        winner_text = WINNER_TEXTS.get(winner)
        if winner_text:
            self.draw_text_with_outline(
                winner_text, sw // 2, sh // 2, self.theme.text, 'notice', 'center',
            )