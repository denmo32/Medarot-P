"""ゲージ計算や時間計算に関連するドメインロジック"""

import math
from config import GAME_PARAMS
from battle.constants import GaugeStatus, TeamType

def calculate_action_times(attack_power: int) -> tuple:
    """攻撃力に基づいてチャージ時間とクールダウン時間を計算（対数スケール）"""
    base_time = 1
    log_modifier = math.log10(attack_power) if attack_power > 0 else 0
    
    # 攻撃力が高いほど時間がかかる
    charging_time = base_time + log_modifier
    cooldown_time = base_time + log_modifier
    
    return charging_time, cooldown_time

def calculate_gauge_ratio(status: str, progress: float) -> float:
    """現在の状態と進捗から、中央への到達度（ポジションレシオ）を計算する。"""
    if status == GaugeStatus.EXECUTING:
        return 1.0
    if status == GaugeStatus.CHARGING:
        return max(0.0, min(1.0, progress / 100.0))
    if status == GaugeStatus.COOLDOWN:
        return max(0.0, min(1.0, 1.0 - (progress / 100.0)))
    return 0.0

def calculate_current_x(base_x: int, status: str, progress: float, team_type: str) -> float:
    """エンティティの現在のアイコンX座標を計算する（ゲージ進行に基づく視覚的座標）"""
    center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
    offset = 40
    ratio = calculate_gauge_ratio(status, progress)
    
    if team_type == TeamType.PLAYER:
        target_x = center_x - offset
        return base_x + ratio * (target_x - base_x)
    else:
        start_x = base_x + GAME_PARAMS['GAUGE_WIDTH']
        target_x = center_x + offset
        return start_x + ratio * (target_x - start_x)
