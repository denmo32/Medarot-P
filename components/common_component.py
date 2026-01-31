"""汎用ECSコンポーネント定義"""

from dataclasses import dataclass
from core.ecs import Component

@dataclass
class PositionComponent(Component):
    """位置コンポーネント"""
    x: int
    y: int

@dataclass
class NameComponent(Component):
    """名前コンポーネント"""
    name: str