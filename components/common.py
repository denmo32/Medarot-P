"""汎用ECSコンポーネント定義"""

from core.ecs import Component

class PositionComponent(Component):
    """位置コンポーネント"""
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

class NameComponent(Component):
    """名前コンポーネント"""
    def __init__(self, name: str):
        self.name = name

