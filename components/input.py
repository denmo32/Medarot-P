"""入力データ用コンポーネント"""

from core.ecs import Component

class InputComponent(Component):
    """ユーザー入力の状態を保持するコンポーネント"""
    def __init__(self):
        # マウス
        self.mouse_x: int = 0
        self.mouse_y: int = 0
        self.mouse_clicked: bool = False  # 左クリックされた瞬間
        
        # キーボード（押下された瞬間のみTrue）
        self.key_z: bool = False      # 決定
        self.key_x: bool = False      # キャンセル
        self.key_left: bool = False
        self.key_right: bool = False
        self.key_up: bool = False
        self.key_down: bool = False
        
        self.escape_pressed: bool = False