"""バトル関連のユーティリティ関数"""

import math


def calculate_action_times(attack_power: int) -> tuple:
    """攻撃力に基づいてチャージ時間とクールダウン時間を計算（対数スケール）
    
    攻撃力が高い → 時間が長い（遅い）
    攻撃力が低い → 時間が短い（速い）
    """
    base_time = 1
    log_modifier = math.log10(attack_power)
    
    charging_time = base_time + log_modifier
    cooldown_time = base_time + log_modifier
    
    return charging_time, cooldown_time
