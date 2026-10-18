"""論理入力DTOおよび入力ソース抽象インターフェース。

Pygame などの外部グラフィック・入力ライブラリに依存せず、
ゲーム側が認識する論理入力の状態のみを定義します。
"""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class InputState:
    """論理入力およびマウス状態を保持する不変データクラス"""
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
