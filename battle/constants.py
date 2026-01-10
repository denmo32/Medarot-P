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
    SWORD = "ソード"
    HAMMER = "ハンマー"
    THUNDER = "サンダー"

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
    EXECUTING = "executing"
    LOG_WAIT = "log_wait"
    GAME_OVER = "game_over"