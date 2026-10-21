"""ゲームロジック関連の設定値"""

FPS = 60

PLAYER_COUNT = 3
ENEMY_COUNT = 3

# === 熟練度（Proficiency）関連のバランス定数 ===
PROFICIENCY_ATTACK_FACTOR: int = 2      # 威力加算 = 適性Lv(1〜5) * 2  （+2 〜 +10）
PROFICIENCY_SUCCESS_DIVISOR: int = 4    # 成功度加算 = 熟練値(0〜99) // 4 （+0 〜 +24）
MAX_MASTERY_VALUE: int = 99            # 熟練値の最大値
EXP_PER_MASTERY_POINT: int = 5          # 熟練値1アップに必要な成功回数
DEFAULT_APTITUDE_LEVEL: int = 1         # 未定義時のフォールバック適性Lv