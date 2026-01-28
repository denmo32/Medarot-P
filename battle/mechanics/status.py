"""状態異常（StatusEffect）の振る舞いロジック"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from components.battle_component import StatusEffect, GaugeComponent

class StatusBehavior(ABC):
    """状態異常の振る舞いを定義する基底クラス"""

    @abstractmethod
    def on_tick(self, effect: StatusEffect, gauge: GaugeComponent, dt: float):
        """毎フレーム更新時に呼ばれる処理"""
        pass

    def can_charge(self, effect: StatusEffect) -> bool:
        """充填・放熱の進行が可能か"""
        return True

    def can_act(self, effect: StatusEffect) -> bool:
        """行動実行が可能か（行動不能ステータス用）"""
        return True


class StopStatus(StatusBehavior):
    """停止：時間が経過するまで充填・放熱が進まない"""
    
    def on_tick(self, effect: StatusEffect, gauge: GaugeComponent, dt: float):
        effect.duration -= dt

    def can_charge(self, effect: StatusEffect) -> bool:
        return False


class StatusRegistry:
    """StatusBehaviorのカタログ"""
    
    _behaviors = {
        "stop": StopStatus(),
    }
    
    # 未定義の効果に対するデフォルト（何もしない、阻害もしない）
    _default = type("DefaultStatus", (StatusBehavior,), {
        "on_tick": lambda self, e, g, dt: setattr(e, 'duration', e.duration - dt),
        "can_charge": lambda self, e: True,
        "can_act": lambda self, e: True
    })()

    @classmethod
    def get(cls, type_id: str) -> StatusBehavior:
        return cls._behaviors.get(type_id, cls._default)