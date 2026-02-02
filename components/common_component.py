"""汎用ECSコンポーネント定義"""

from dataclasses import dataclass
from core.ecs import Component

@dataclass
class PositionComponent(Component):
    """位置コンポーネント (比率 0.0 ~ 1.0)"""
    x: float
    y: float

@dataclass
class NameComponent(Component):
    """名前コンポーネント"""
    name: str