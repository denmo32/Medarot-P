"""ターゲットレーダー演出の時間軸・進行を一元管理するディレクター。

UI や Pygame には依存せず、純粋な論理時間 dt から移動進捗と拡縮スケールを計算します。
"""
import math
from dataclasses import dataclass

from features.battle.constants import BattleTiming


@dataclass(frozen=True)
class RadarAnimationState:
    """レーダーの瞬間的な表示パラメータ（イミュータブルDTO）"""
    travel_progress: float  # 0.0 (攻撃者位置) 〜 1.0 (対象位置)
    scale: float            # 拡縮倍率 (通常 1.0、パルス時最大 1.35)


class TargetRadarDirector:
    """ターゲットレーダーの時間軸アニメーション（移動・パルス）を管理するディレクター。"""

    def __init__(
        self,
        attacker_index: int,
        target_index: int,
        travel_duration: float = BattleTiming.TARGET_RADAR_TRAVEL,
        pulse_duration: float = BattleTiming.TARGET_RADAR_PULSE,
        pulse_count: int = BattleTiming.TARGET_RADAR_PULSE_COUNT,
    ):
        self.attacker_index = attacker_index
        self.target_index = target_index
        self.is_same_target = (attacker_index == target_index)
        self.travel_duration = 0.0 if self.is_same_target else max(0.001, travel_duration)
        self.pulse_duration = max(0.001, pulse_duration)
        self.pulse_count = pulse_count
        self.elapsed = 0.0

    def update(self, dt: float):
        """論理時間を進行させる"""
        self.elapsed += max(0.0, dt)

    def evaluate(self, is_static: bool = False) -> RadarAnimationState:
        """現在の時間軸における移動進捗（ease-out適用済み）とスケールを計算して返す（純粋計算）"""
        if is_static:
            return RadarAnimationState(travel_progress=1.0, scale=1.0)

        total_pulse_time = self.pulse_duration * self.pulse_count

        # 1. 攻撃者から対象への移動フェーズ
        if self.elapsed < self.travel_duration and self.travel_duration > 0:
            t = self.elapsed / self.travel_duration
            ease_t = 1.0 - (1.0 - t) ** 2
            return RadarAnimationState(travel_progress=ease_t, scale=1.0)

        # 2. 対象到達後のパルス（拡縮）フェーズ
        pulse_elapsed = self.elapsed - self.travel_duration
        if 0.0 <= pulse_elapsed < total_pulse_time:
            cycle_progress = (pulse_elapsed % self.pulse_duration) / self.pulse_duration
            open_ratio = math.sin(cycle_progress * math.pi)
            scale = 1.0 + 0.35 * open_ratio
            return RadarAnimationState(travel_progress=1.0, scale=scale)

        # 3. パルス完了後の静止フェーズ
        return RadarAnimationState(travel_progress=1.0, scale=1.0)
