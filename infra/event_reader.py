"""Pygame イベントを論理入力 (InputState) に変換するアダプター。"""
from typing import Dict, Optional
import pygame

from core.inputs import InputState, EventReaderProtocol


# デフォルトのキーマッピング (pygameキーコード -> InputStateの属性名)
DEFAULT_KEY_MAP: Dict[int, str] = {
    pygame.K_z: 'btn_ok',
    pygame.K_RETURN: 'btn_ok',
    pygame.K_SPACE: 'btn_ok',
    pygame.K_x: 'btn_cancel',
    pygame.K_BACKSPACE: 'btn_cancel',
    pygame.K_ESCAPE: 'btn_menu',
    pygame.K_LEFT: 'btn_left',
    pygame.K_a: 'btn_left',
    pygame.K_RIGHT: 'btn_right',
    pygame.K_d: 'btn_right',
    pygame.K_UP: 'btn_up',
    pygame.K_w: 'btn_up',
    pygame.K_DOWN: 'btn_down',
    pygame.K_s: 'btn_down',
}


class PygameEventReader:
    """Pygame のイベントループを回し、論理入力 InputState を更新するクラス。"""

    def __init__(self, key_map: Optional[Dict[int, str]] = None):
        self._state = InputState()
        self.key_map = key_map if key_map is not None else dict(DEFAULT_KEY_MAP)

    @property
    def state(self) -> InputState:
        return self._state

    def handle_events(self) -> bool:
        """Pygame イベントを処理し、論理入力状態を更新する。

        Returns:
            bool: 正常継続なら True、ウィンドウ終了 (QUIT) なら False。
        """
        self._state.reset()
        self._state.mouse_x, self._state.mouse_y = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._state.mouse_clicked = True
            elif event.type == pygame.KEYDOWN:
                attr = self.key_map.get(event.key)
                if attr:
                    setattr(self._state, attr, True)

        return True