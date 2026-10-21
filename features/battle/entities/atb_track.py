"""単一機体のATBゲージ進行と端到達イベントの追跡メカニクス。

ATBゲージの状態遷移図:

         [ READY ] ──(start_charge)──> [ CHARGING ] ──(pos >= 1.0)──> [ CHARGED (イベント)]
             ▲                               │                                │
             │                               │ abort_charge_to_cooldown()     │ start_execution()
             │                               │ (割り込み中断: 現在地から後退)   ▼
             │                               ▼                         [ EXECUTING ]
             └──(pos <= 0.0)────────── [ COOLDOWN ] <─────────────────────────┘
                   COOLED (イベント)                     enter_cooldown_from_execution()
                   └─> enter_ready()                     (行動完了/中止: 1.0から後退)

イベント発行契機:
  - ATBEvent.CHARGED: CHARGING 状態の進行度が 1.0 に到達した瞬間
  - ATBEvent.COOLED:  COOLDOWN 状態の進行度が 0.0 に到達した瞬間
"""
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
        """待機(0.0)から充填開始"""
        self.charge_duration = max(0.001, duration)
        self.cooldown_duration = max(0.001, duration)
        self.status = GaugeStatus.CHARGING
        self.position = 0.0

    def start_execution(self):
        """中央実行ライン(1.0)へ到達し、行動実行へ入る"""
        self.status = GaugeStatus.EXECUTING
        self.position = 1.0

    def enter_cooldown_from_execution(self):
        """行動完了、または中央ラインでの不発・中止により端(1.0)から放熱開始"""
        self.status = GaugeStatus.COOLDOWN
        self.position = 1.0

    def abort_charge_to_cooldown(self):
        """充填中の割り込み中断（パーツ破壊・ターゲット喪失）。現在位置から直ちに放熱開始"""
        self.status = GaugeStatus.COOLDOWN
        # position はリセットせず現在位置を維持

    def enter_ready(self):
        """放熱完了により待機(0.0)へ復帰"""
        self.status = GaugeStatus.READY
        self.position = 0.0

    def advance(self, dt: float, is_paused: bool = False) -> Optional[ATBEvent]:
        """時間を進行させ、端到達イベントを返す（状態遷移自体は外側の指示に従う）"""
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