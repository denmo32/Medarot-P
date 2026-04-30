"""状態異常（StatusEffect）の振る舞いロジック"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.models import StatusEffect

class StatusBehavior(ABC):
    """状態異常の振る舞いを定義する基底クラス"""

    def can_charge(self, effect: StatusEffect) -> bool:
        """充填・放熱の進行が可能か"""
        return True

    def can_act(self, effect: StatusEffect) -> bool:
        """行動実行が可能か（行動不能ステータス用）"""
        return True


class StopStatus(StatusBehavior):
    """停止：時間が経過するまで充填・放熱が進まない"""
    def can_charge(self, effect: StatusEffect) -> bool:
        return False


_behaviors = {
    "stop": StopStatus(),
}

class DefaultStatus(StatusBehavior):
    pass

_default = DefaultStatus()

def get_status_behavior(type_id: str) -> StatusBehavior:
    """指定された状態異常種別の振る舞いを取得する。"""
    return _behaviors.get(type_id, _default)
