from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

__all__ = [
    "BattlePhase",
    "CutinStep",
    "PhaseConfig",
    "PHASE_CONFIGS",
    "INTERRUPTIBLE_PHASES",
    "ADVANCEABLE_PHASES",
    "TARGET_RADAR_PHASES",
    "TARGET_RADAR_STATIC_PHASES",
    "BattleTiming",
]


class BattlePhase(str, Enum):
    """戦闘の進行フェーズ"""
    INITIAL_SETUP = "initial_setup"
    IDLE = "idle"
    INPUT = "input"
    TARGET_INDICATION = "target_indication"
    ATTACK_DECLARATION = "attack_declaration"
    CUTIN = "cutin"
    CUTIN_RESULT = "cutin_result"
    LOG_WAIT = "log_wait"
    GAME_OVER = "game_over"
    OPENING_LOG = "opening_log"
    OPENING_POPUP = "opening_popup"


class CutinStep(str, Enum):
    """カットイン演出のステップ（第1段階：主攻撃、第2段階：貫通）"""
    PRIMARY = "primary"
    PIERCE = "pierce"


INTERRUPTIBLE_PHASES = (BattlePhase.IDLE,)
ADVANCEABLE_PHASES = (
    BattlePhase.OPENING_LOG,
    BattlePhase.OPENING_POPUP,
    BattlePhase.ATTACK_DECLARATION,
    BattlePhase.CUTIN_RESULT,
    BattlePhase.LOG_WAIT,
)
TARGET_RADAR_PHASES = (
    BattlePhase.TARGET_INDICATION,
    BattlePhase.ATTACK_DECLARATION,
    BattlePhase.CUTIN,
    BattlePhase.CUTIN_RESULT,
)
TARGET_RADAR_STATIC_PHASES = (
    BattlePhase.ATTACK_DECLARATION,
    BattlePhase.CUTIN,
    BattlePhase.CUTIN_RESULT,
)


class BattleTiming:
    """演出やフェーズ遷移のタイミング（秒）および表示仕様定数"""
    TARGET_INDICATION = 0.8
    OPENING_POPUP = 1.5
    LOG_DISPLAY_MAX = 3
    # ターゲットレーダー演出
    TARGET_RADAR_TRAVEL = 0.3
    TARGET_RADAR_PULSE = 0.22
    TARGET_RADAR_PULSE_COUNT = 2


@dataclass(frozen=True)
class PhaseConfig:
    duration: float = 0.0
    next_phase: Optional[BattlePhase] = None


PHASE_CONFIGS: Dict[BattlePhase, PhaseConfig] = {
    BattlePhase.OPENING_LOG: PhaseConfig(next_phase=BattlePhase.OPENING_POPUP),
    BattlePhase.OPENING_POPUP: PhaseConfig(
        duration=BattleTiming.OPENING_POPUP, next_phase=BattlePhase.IDLE
    ),
    BattlePhase.TARGET_INDICATION: PhaseConfig(
        duration=BattleTiming.TARGET_INDICATION, next_phase=BattlePhase.ATTACK_DECLARATION
    ),
    BattlePhase.CUTIN: PhaseConfig(
        next_phase=BattlePhase.CUTIN_RESULT
    ),
}