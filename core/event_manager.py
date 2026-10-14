"""Pygame イベントを論理入力 (InputState) に変換するモジュール。"""
import pygame
from dataclasses import dataclass

@dataclass
class InputState:
    """論理入力およびマウス状態を保持するデータクラス"""
    btn_ok: bool = False
    btn_cancel: bool = False
    btn_menu: bool = False
    btn_left: bool = False
    btn_right: bool = False
    btn_up: bool = False
    btn_down: bool = False
    mouse_x: int = 0
    mouse_y: int = 0
    mouse_clicked: bool = False

    def reset(self):
        self.btn_ok = False
        self.btn_cancel = False
        self.btn_menu = False
        self.btn_left = False
        self.btn_right = False
        self.btn_up = False
        self.btn_down = False
        self.mouse_clicked = False


KEY_MAP = {
    pygame.K_z: 'btn_ok', pygame.K_RETURN: 'btn_ok', pygame.K_SPACE: 'btn_ok',
    pygame.K_x: 'btn_cancel', pygame.K_BACKSPACE: 'btn_cancel',
    pygame.K_ESCAPE: 'btn_menu',
    pygame.K_LEFT: 'btn_left', pygame.K_a: 'btn_left',
    pygame.K_RIGHT: 'btn_right', pygame.K_d: 'btn_right',
    pygame.K_UP: 'btn_up', pygame.K_w: 'btn_up',
    pygame.K_DOWN: 'btn_down', pygame.K_s: 'btn_down',
}


class EventManager:
    """Pygame イベントを論理入力 (InputState) に一元変換する。"""

    def __init__(self):
        self.state = InputState()

    def handle_events(self) -> bool:
        """戻り値：False なら終了シグナル。"""
        self.state.reset()
        self.state.mouse_x, self.state.mouse_y = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.state.mouse_clicked = True
            elif event.type == pygame.KEYDOWN and event.key in KEY_MAP:
                setattr(self.state, KEY_MAP[event.key], True)

        return True