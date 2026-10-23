# features/battle/atb_system.py
"""ATBゲージ進行および待機キューの管理を一元化するシステム。"""
from typing import List, Optional, Tuple, TYPE_CHECKING
from .entities.atb_track import ATBEvent

if TYPE_CHECKING:
    from .entities.robot import Robot


class ATBSystem:
    """全機体のATBゲージ進行とイベント収集に専念するシステム（純粋なATB進行のみ）"""

    def __init__(self, robots: List['Robot']):
        self.robots = robots
        self.turn_queue: List[Tuple['Robot', ATBEvent]] = []

    def update(self, dt: float):
        """全機体のATBゲージを進行させ、端到達イベントをキューに収集する"""
        for robot in self.robots:
            event = robot.tick_atb(dt)
            if event in (ATBEvent.CHARGED, ATBEvent.COOLED):
                if not any(r is robot for r, _ in self.turn_queue):
                    self.turn_queue.append((robot, event))

    def pop_next_turn(self) -> Optional[Tuple['Robot', ATBEvent]]:
        """次の手番機体と発生イベントのペアを取得する"""
        while self.turn_queue:
            robot, event = self.turn_queue.pop(0)
            if robot.is_alive:
                return robot, event
        return None