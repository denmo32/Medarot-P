"""ATBゲージと時間補正の計算式"""

import math


def calculate_base_time(attack_power: int) -> float:
    """攻撃力に基づく基本時間（充填・放熱で共用）の計算（対数スケール）"""
    if attack_power <= 0:
        return 1.0
    return 1.0 + math.log10(attack_power)
