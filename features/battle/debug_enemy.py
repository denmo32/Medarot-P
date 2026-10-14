"""バトル編成のデバッグ設定モジュール。

このファイルの設定を変更することで、機体数（1vs1, 1vs3, 2vs2 など）や
相手チームの編成を自由にカスタマイズしてバトルを開始できます。

【設定の例】
  - 1vs1 で戦う場合:
      DEBUG_PLAYER_COUNT = 1
      DEBUG_ENEMY_COUNT = 1
  - 1vs3 で戦う場合:
      DEBUG_PLAYER_COUNT = 1
      DEBUG_ENEMY_COUNT = 3
  - カスタム敵（特定パーツ構成）と戦う場合:
      ENABLE_CUSTOM_ENEMY = True
      （CUSTOM_ENEMY_SETUPS に定義した機体数がそのまま敵数になります）
"""

from typing import List, Dict, Any, Optional

# ==============================================================================
# 1. 機体数設定（人数デバッグ・バランス調整）
# ==============================================================================
# 出撃機体数を制限したい場合に数値を指定（1〜3）。None の場合はデフォルト設定（3機）を使用。
DEBUG_PLAYER_COUNT: Optional[int] = 3
DEBUG_ENEMY_COUNT: Optional[int] = 3

# ==============================================================================
# 2. 相手チーム（エネミー）編成カスタマイズ
# ==============================================================================
# カスタム敵編成を有効にするフラグ（True で下記の CUSTOM_ENEMY_SETUPS を使用）
ENABLE_CUSTOM_ENEMY: bool = False

# 相手チームの機体構成リスト（インデックス 0 がリーダー機となります）
# ※ DEBUG_ENEMY_COUNT が未指定の場合、このリストに指定した機体数がそのまま敵数になります。
# ※ 一部の部位が未指定の場合は、自動的にデフォルトパーツで補完されます。
CUSTOM_ENEMY_SETUPS: List[Dict[str, Any]] = [
    # 1機目（リーダー機）
    {
        "name": "めたびー",
        "medal": "medal_001",
        "parts": {
            "head": "head_001",
            "right_arm": "rarm_001",
            "left_arm": "larm_001",
            "legs": "legs_001",
        }
    },
    # 2機目
    {
        "name": "メタビー",
        "medal": "medal_001",
        "parts": {
            "head": "head_002",
            "right_arm": "rarm_002",
            "left_arm": "larm_002",
            "legs": "legs_002",
        }
    },
    # 3機目
    {
        "name": "メタルビートル",
        "medal": "medal_001",
        "parts": {
            "head": "head_003",
            "right_arm": "rarm_003",
            "left_arm": "larm_003",
            "legs": "legs_003",
        }
    },
]