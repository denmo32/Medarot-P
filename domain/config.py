# domain/config.py
"""ゲームロジック関連の設定値およびフォールバック定義"""
from typing import Dict
from domain.constants import PartType

FPS = 60

PLAYER_COUNT = 3
ENEMY_COUNT = 3

DEFAULT_MEDAL_ID = "medal_001"

DEFAULT_FALLBACK_PART_IDS: Dict[PartType, str] = {
    PartType.HEAD: "head_001",
    PartType.RIGHT_ARM: "right_arm_001",
    PartType.LEFT_ARM: "left_arm_001",
    PartType.LEGS: "legs_001",
}