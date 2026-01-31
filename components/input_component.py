"""入力データ用コンポーネント"""

from dataclasses import dataclass
from core.ecs import Component

@dataclass
class InputComponent(Component):
    """ユーザー入力の状態（論理入力）を保持するコンポーネント"""
    # マウス座標・クリック
    mouse_x: int = 0
    mouse_y: int = 0
    mouse_clicked: bool = False  # 左クリックされた瞬間
    
    # 論理ボタンフラグ（押下された瞬間のみTrue）
    btn_ok: bool = False      # 決定 (Z, Enter, Click)
    btn_cancel: bool = False  # キャンセル (X, Backspace)
    btn_menu: bool = False    # メニュー/中断 (Esc)
    
    # 方向入力
    btn_left: bool = False
    btn_right: bool = False
    btn_up: bool = False
    btn_down: bool = False