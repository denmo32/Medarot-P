"""バトル編成のデバッグ設定モジュール。

このファイルの設定を変更することで、機体数（1vs1, 1vs3, 2vs2 など）や
相手チームの編成を自由にカスタマイズしてバトルを開始できます。
"""

from typing import List, Dict, Any, Optional

# ==============================================================================
# 1. 機体数設定（人数デバッグ・バランス調整）
# ==============================================================================
DEBUG_PLAYER_COUNT: Optional[int] = 3
DEBUG_ENEMY_COUNT: Optional[int] = 3

# ==============================================================================
# 2. 相手チーム（エネミー）編成カスタマイズ
# ==============================================================================
ENABLE_CUSTOM_ENEMY: bool = False

CUSTOM_ENEMY_SETUPS: List[Dict[str, Any]] = [
    # 1機目（リーダー機）
    {
        "name": "めたびー",
        "medal": "medal_001",
        "parts": {
            "head": "head_001",
            "right_arm": "right_arm_001",
            "left_arm": "left_arm_001",
            "legs": "legs_001",
        }
    },
    # 2機目
    {
        "name": "メタビー",
        "medal": "medal_001",
        "parts": {
            "head": "head_002",
            "right_arm": "right_arm_002",
            "left_arm": "left_arm_002",
            "legs": "legs_002",
        }
    },
    # 3機目
    {
        "name": "メタルビートル",
        "medal": "medal_001",
        "parts": {
            "head": "head_003",
            "right_arm": "right_arm_003",
            "left_arm": "left_arm_003",
            "legs": "legs_003",
        }
    },
]