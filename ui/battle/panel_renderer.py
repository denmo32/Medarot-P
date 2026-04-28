"""メッセージウィンドウ、アクションメニュー、リザルトの描画"""

import pygame
from ui.config import COLORS, UI_PARAMS

class UIPanelRenderer:
    def __init__(self, master):
        self.master = master # master は BattleRenderer インスタンス

    def render(self, snapshot):
        # 行動選択中とそれ以外で背景の描画順序が変わるため、順番に制御
        if snapshot.action_menu.is_active:
            self._render_action_menu(snapshot.action_menu)
        elif snapshot.log_window.is_active:
            self._render_log_window(snapshot.log_window)

        if snapshot.opening_popup_text:
            self._render_opening_popup(snapshot.opening_popup_text)

        if snapshot.game_over.is_active:
            self._render_game_over(snapshot.game_over)

    def _render_opening_popup(self, text):
        sw, sh = self.master.get_screen_size()
        mid_x, mid_y = sw // 2, sh // 2
        # 中央に大きく表示 (notice フォントを使用)
        self.master.draw_text_with_outline(text, mid_x, mid_y, COLORS['TEXT'], 'notice', 'center')

    def _render_log_window(self, data):
        sw, sh = self.master.get_screen_size()

        wy = self.master.scale_y(UI_PARAMS['MESSAGE_WINDOW_Y_RATIO'])
        wh = self.master.scale_y(UI_PARAMS['MESSAGE_WINDOW_HEIGHT_RATIO'])
        pad = self.master.scale_x(UI_PARAMS['MESSAGE_WINDOW_PADDING_RATIO'])

        line_h = int(sh * 0.04)

        # パイプ装飾付きボックスの描画
        self.master.draw_pipe_box((0, wy, sw, wh), COLORS['MSG_BG'], COLORS['MSG_PIPE'], COLORS['MSG_JOINT'])

        for i, log in enumerate(data.logs):
            # テキストは黒
            self.master.draw_text(log, (pad, wy + pad + i * line_h), color=COLORS['MSG_TEXT'], font_type='medium')

        if data.show_input_guidance:
            next_off_x = self.master.scale_x(0.3)
            next_off_y = self.master.scale_y(0.05)
            self.master.draw_text("Z キー or クリックで次に進む",
                           (sw - next_off_x, wy + wh - next_off_y), color=COLORS['MSG_TEXT'], font_type='medium')

    def _render_action_menu(self, data):
        sw, sh = self.master.get_screen_size()
        wy = self.master.scale_y(UI_PARAMS['MESSAGE_WINDOW_Y_RATIO'])
        wh = self.master.scale_y(UI_PARAMS['MESSAGE_WINDOW_HEIGHT_RATIO'])
        pad = self.master.scale_x(UI_PARAMS['MESSAGE_WINDOW_PADDING_RATIO'])

        # 行動選択時は、通常のメッセージウィンドウの代わりに単色の暗いパネルを描画
        pygame.draw.rect(self.master.screen, COLORS['ACTION_MENU_BG'], (0, wy, sw, wh))

        # 機体名をパネルの左上に表示
        self.master.draw_text(f"{data.actor_name}", (pad, wy + pad), color=COLORS['TEXT'], font_type='medium')

        # フォーカス中のパーツのスキルを表示
        if 0 <= data.selected_index < len(data.buttons):
            selected_btn = data.buttons[data.selected_index]
            if selected_btn.skill_label:
                # 機体名の下に配置
                skill_y = wy + pad + int(sh * 0.05)
                self.master.draw_text(f"{selected_btn.skill_label}", (pad, skill_y), (200, 255, 100), 'medium')

        # 描画時にその場でレイアウトを計算
        from .ui_hit_tester import UIHitTester
        layouts = UIHitTester.calculate_action_menu_layout(len(data.buttons), (sw, sh))

        for i, btn in enumerate(data.buttons):
            is_selected = (i == data.selected_index)
            rect = layouts[i]

            if not btn.enabled:
                bg = COLORS['BUTTON_DISABLED_BG']
                text_color = (150, 150, 150)
                border = COLORS['BUTTON_BORDER']
            elif is_selected:
                bg = COLORS['ACTION_BTN_FOCUS_BG']
                text_color = COLORS['ACTION_BTN_FOCUS_TEXT']
                border = COLORS['BUTTON_BORDER']
            else:
                bg = COLORS['ACTION_BTN_NORMAL_BG']
                text_color = COLORS['ACTION_BTN_NORMAL_TEXT']
                border = COLORS['BUTTON_BORDER']

            self.master.draw_box(rect, bg, border, 2)
            font_type = 'action_button_focus' if is_selected else 'action_button'
            self.master.draw_text(btn.label, rect.center, color=text_color, font_type=font_type, align='center')

    def _render_game_over(self, data):
        sw, sh = self.master.get_screen_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill(COLORS['NOTICE_BG'])
        self.master.screen.blit(overlay, (0, 0))

        color = COLORS['PLAYER'] if data.winner == "プレイヤー" else COLORS['ENEMY']
        mid_x, mid_y = sw // 2, sh // 2

        # BaseRenderer に移設したメソッドを使用。強調のため large/center を指定
        self.master.draw_text_with_outline(f"{data.winner} の勝利！", mid_x, mid_y, color, 'notice', 'center')

        notice_off_y = int(sh * 0.08)
