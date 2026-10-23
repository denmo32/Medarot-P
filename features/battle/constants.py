"""戦闘関連の定数定義"""

__all__ = [
    "BattleTiming",
]


class BattleTiming:
    """演出の所要秒数および表示仕様定数"""
    OPENING_POPUP = 1.5
    LOG_DISPLAY_MAX = 3
    TARGET_INDICATION = 0.8
    TARGET_RADAR_TRAVEL = 0.3
    TARGET_RADAR_PULSE = 0.22
    TARGET_RADAR_PULSE_COUNT = 2