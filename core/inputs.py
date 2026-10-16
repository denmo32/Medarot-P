"""論理入力DTOおよび入力ソース抽象インターフェース。

Pygame などの外部グラフィック・入力ライブラリに依存せず、
ゲーム側が認識する論理入力の状態のみを定義します。
"""
from dataclasses import dataclass
from typing import Protocol


@dataclass
class InputState:
    """論理入力およびマウス状態を保持する純粋データクラス"""
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

    def reset(self) -> None:
        """次フレームの判定に向けて入力をリセット"""
        self.btn_ok = False
        self.btn_cancel = False
        self.btn_menu = False
        self.btn_left = False
        self.btn_right = False
        self.btn_up = False
        self.btn_down = False
        self.mouse_clicked = False


class EventReaderProtocol(Protocol):
    """入力イベントを読み取り InputState を提供するプロトコル"""

    @property
    def state(self) -> InputState:
        ...

    def handle_events(self) -> bool:
        """イベントを処理し、InputState を更新する。
        
        Returns:
            bool: ゲームを継続する場合は True、終了シグナルを受信した場合は False。
        """
        ...