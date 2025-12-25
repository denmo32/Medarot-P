"""入力データ用コンポーネント"""

from core.ecs import Component

class InputComponent(Component):
    """ユーザー入力の状態を保持するコンポーネント"""
    def __init__(self):
        self.mouse_x: int = 0
        self.mouse_y: int = 0
        self.mouse_clicked: bool = False  # 左クリックされた瞬間のみTrue
        self.escape_pressed: bool = False
