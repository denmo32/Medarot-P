"""バトル進行に特化した定数定義"""
from domain.constants import TeamType, PartType, ActionType, GaugeStatus, TraitType, AttributeType

class BattlePhase:
    IDLE = "idle"
    INPUT = "input"
    ENEMY_TURN = "enemy_turn"
    TARGET_INDICATION = "target_indication"
    ATTACK_DECLARATION = "attack_declaration"
    CUTIN = "cutin"
    CUTIN_RESULT = "cutin_result"
    EXECUTING = "executing"
    LOG_WAIT = "log_wait"
    GAME_OVER = "game_over"

class BattleTiming:
    """演出やフェーズ遷移のタイミング（秒）"""
    TARGET_INDICATION = 0.8
    # 演出時間を延長 (スライド演出のため)
    CUTIN_ANIMATION = 2.5

# UI表示用の部位名称マップ
PART_LABELS = {
    PartType.HEAD: "頭部",
    PartType.RIGHT_ARM: "右腕",
    PartType.LEFT_ARM: "左腕",
    PartType.LEGS: "脚部"
}

# アクションメニューのパーツ表示順序
MENU_PART_ORDER = [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]

# チームごとの設定（ゲージ速度、カラー）
TEAM_SETTINGS = {
    TeamType.PLAYER: {
        'gauge_speed': 0.3,
        'color': (0, 100, 200) # Blue
    },
    TeamType.ENEMY: {
        'gauge_speed': 0.25,
        'color': (200, 0, 0)   # Red
    }
}
