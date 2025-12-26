"""バトル関連のユーティリティ関数"""

import math
from config import GAME_PARAMS

def calculate_action_times(attack_power: int) -> tuple:
    """攻撃力に基づいてチャージ時間とクールダウン時間を計算（対数スケール）"""
    base_time = 1
    log_modifier = math.log10(attack_power) if attack_power > 0 else 0
    
    charging_time = base_time + log_modifier
    cooldown_time = base_time + log_modifier
    
    return charging_time, cooldown_time

def calculate_current_x(base_x: int, status: str, progress: float, team_type: str) -> float:
    """エンティティの現在のアイコンX座標を計算する（ゲージ進行に基づく視覚的座標）"""
    center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
    offset = 40 # 実行地点のセンターからのオフセット
    
    if team_type == "player":
        # プレイヤー側：右（中央）に向かって進む
        # 待機位置: base_x, 実行位置: center_x - offset
        target_x = center_x - offset
        if status == "charging":
            return base_x + (progress / 100.0) * (target_x - base_x)
        if status == "executing":
            return target_x
        if status == "cooldown":
            return target_x - (progress / 100.0) * (target_x - base_x)
        return base_x
    else:
        # エネミー側：左（中央）に向かって進む
        # 待機位置: base_x + gauge_width, 実行位置: center_x + offset
        start_x = base_x + GAME_PARAMS['GAUGE_WIDTH']
        target_x = center_x + offset
        if status == "charging":
            return start_x - (progress / 100.0) * (start_x - target_x)
        if status == "executing":
            return target_x
        if status == "cooldown":
            return target_x + (progress / 100.0) * (start_x - target_x)
        return start_x