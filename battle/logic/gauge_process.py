"""ゲージ計算や時間計算に関連するドメインロジック"""

import math
from battle.constants import GaugeStatus

def calculate_action_times(attack_power: int) -> tuple:
    """攻撃力に基づいてチャージ時間とクールダウン時間を計算（対数スケール）"""
    base_time = 1
    log_modifier = math.log10(attack_power) if attack_power > 0 else 0
    
    # 攻撃力が高いほど時間がかかる
    charging_time = base_time + log_modifier
    cooldown_time = base_time + log_modifier
    
    return charging_time, cooldown_time

def calculate_gauge_ratio(status: str, progress: float) -> float:
    """現在の状態と進捗から、中央への到達度（ポジションレシオ 0.0 ~ 1.0）を計算する。"""
    if status == GaugeStatus.EXECUTING:
        return 1.0
    if status == GaugeStatus.CHARGING:
        return max(0.0, min(1.0, progress / 100.0))
    if status == GaugeStatus.COOLDOWN:
        return max(0.0, min(1.0, 1.0 - (progress / 100.0)))
    return 0.0