"""ATBゲージ進行および待機キューの管理を一元化するシステム。"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple, TYPE_CHECKING
from domain.constants import GaugeStatus

if TYPE_CHECKING:
    from .models import Robot


class ATBEvent(Enum):
    """ATBの端到達イベント"""
    CHARGED = auto()
    COOLED = auto()


@dataclass
class ATBTrack:
    position: float = 0.0
    status: GaugeStatus = GaugeStatus.READY
    charge_duration: float = 1.0
    cooldown_duration: float = 1.0

    def start_charge(self, duration: float):
        self.charge_duration = max(0.001, duration)
        self.cooldown_duration = max(0.001, duration)
        self.status = GaugeStatus.CHARGING
        self.position = 0.0

    def start_execution(self):
        self.status = GaugeStatus.EXECUTING
        self.position = 1.0

    def enter_cooldown(self, interrupted: bool = False):
        self.status = GaugeStatus.COOLDOWN
        if not interrupted:
            self.position = 1.0

    def enter_ready(self):
        self.status = GaugeStatus.READY
        self.position = 0.0

    def advance(self, dt: float, is_paused: bool = False) -> Optional[ATBEvent]:
        if is_paused:
            return None

        if self.status == GaugeStatus.CHARGING:
            self.position += dt / self.charge_duration
            if self.position >= 1.0:
                self.position = 1.0
                return ATBEvent.CHARGED

        elif self.status == GaugeStatus.COOLDOWN:
            self.position -= dt / self.cooldown_duration
            if self.position <= 0.0:
                self.position = 0.0
                return ATBEvent.COOLED

        return None


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