"""単一機体のATBゲージ進行と端到達イベントの追跡メカニクス。"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional
from domain.constants import GaugeStatus


class ATBEvent(Enum):
    """ATBの端到達イベント"""
    CHARGED = auto()
    COOLED = auto()


@dataclass
class ATBTrack:
    """単一機体のゲージ進行を追跡する純粋データクラス"""
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