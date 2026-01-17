"""バトル関連の定数定義"""

class TeamType:
    PLAYER = "player"
    ENEMY = "enemy"

class PartType:
    HEAD = "head"
    RIGHT_ARM = "right_arm"
    LEFT_ARM = "left_arm"
    LEGS = "legs"

class TraitType:
    # 射撃系
    RIFLE = "ライフル"
    GATLING = "ガトリング"
    # 格闘系
    SWORD = "ソード"
    HAMMER = "ハンマー"
    THUNDER = "サンダー"

    MELEE_TRAITS = [SWORD, HAMMER, THUNDER]
    SHOOTING_TRAITS = [RIFLE, GATLING]

class ActionType:
    ATTACK = "attack"
    SKIP = "skip"

class GaugeStatus:
    CHARGING = "charging"
    EXECUTING = "executing"
    COOLDOWN = "cooldown"
    ACTION_CHOICE = "action_choice"

class BattlePhase:
    IDLE = "idle"
    INPUT = "input"
    TARGET_INDICATION = "target_indication"
    ATTACK_DECLARATION = "attack_declaration"
    CUTIN = "cutin"
    CUTIN_RESULT = "cutin_result"           # 追加: カットイン結果表示
    EXECUTING = "executing"
    LOG_WAIT = "log_wait"
    GAME_OVER = "game_over"

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