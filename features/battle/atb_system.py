"""ATBゲージ進行および待機キューの管理を一元化するシステム。"""
from typing import List, Optional, Tuple, TYPE_CHECKING
from .entities.atb_track import ATBEvent

if TYPE_CHECKING:
    from .entities.robot import Robot


class ATBSystem:
    def __init__(self, robots: List['Robot']):
        self.robots = robots
        self.turn_queue: List[Tuple['Robot', ATBEvent]] = []

    def update(self, dt: float):
        """【Hollywood Principle】機体に自律進行を命じ、端到達イベントをペアでキューに積む"""
        for robot in self.robots:
            event = robot.tick(dt)
            if event in (ATBEvent.CHARGED, ATBEvent.COOLED):
                # 同一機体が既に待機中の場合は重複追加しない（先勝ち）
                if not any(r is robot for r, _ in self.turn_queue):
                    self.turn_queue.append((robot, event))

    def pop_next_turn(self) -> Optional[Tuple['Robot', ATBEvent]]:
        """次の手番機体と発生イベントのペアを取得する"""
        while self.turn_queue:
            robot, event = self.turn_queue.pop(0)
            if robot.is_alive:
                return robot, event
        return None