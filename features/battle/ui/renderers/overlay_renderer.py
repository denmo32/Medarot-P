"""オープニングやゲームオーバーなどのオーバーレイを描画する（テーマ色適用）。"""
import pygame

from domain.constants import TeamType
from ui_base.renderer import BaseRenderer
from features.battle.presentation.view_models import OverlayModel

OPENING_POPUP_TEXT = "ロボトルファイト！"
WINNER_TEXTS = {
    TeamType.PLAYER: "WIN！",
    TeamType.ENEMY: "LOSE...",
}


class OverlayRenderer(BaseRenderer):
    def render(self, model: OverlayModel):
        screen_size = self.get_screen_size()

        if model.opening_popup_visible:
            self.render_opening_popup(screen_size)

        if model.game_over_winner is not None:
            self.render_game_over(model.game_over_winner, screen_size)

    def render_opening_popup(self, screen_size):
        sw, sh = screen_size
        self.draw_text_with_outline(
            OPENING_POPUP_TEXT, sw // 2, sh // 2, self.theme.text, 'notice', 'center',
        )

    def render_game_over(self, winner, screen_size):
        sw, sh = screen_size

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill(self.theme.notice_bg)
        self.screen.blit(overlay, (0, 0))

        winner_text = WINNER_TEXTS.get(winner)
        if winner_text:
            self.draw_text_with_outline(
                winner_text, sw // 2, sh // 2, self.theme.text, 'notice', 'center',
            )