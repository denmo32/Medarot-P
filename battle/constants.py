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
    OPENING_LOG = "opening_log"
    OPENING_POPUP = "opening_popup"

class BattleTiming:
    """演出やフェーズ遷移のタイミング（秒）"""
    TARGET_INDICATION = 0.8
    # 演出時間を延長 (スライド演出のため)
    CUTIN_ANIMATION = 2.5