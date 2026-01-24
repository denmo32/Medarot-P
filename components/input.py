"""入力データ用コンポーネント"""

from core.ecs import Component

class InputComponent(Component):
    """ユーザー入力の状態（論理入力）を保持するコンポーネント"""
    def __init__(self):
        # マウス座標・クリック
        self.mouse_x: int = 0
        self.mouse_y: int = 0
        self.mouse_clicked: bool = False  # 左クリックされた瞬間
        
        # 論理ボタンフラグ（押下された瞬間のみTrue）
        self.btn_ok: bool = False      # 決定 (Z, Enter, Click)
        self.btn_cancel: bool = False  # キャンセル (X, Backspace)
        self.btn_menu: bool = False    # メニュー/中断 (Esc)
        
        # 方向入力
        self.btn_left: bool = False
        self.btn_right: bool = False
        self.btn_up: bool = False
        self.btn_down: bool = False