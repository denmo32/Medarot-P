from enum import Enum

__all__ = [
    "BattlePhase",
    "CutinStep",
    "TARGET_RADAR_PHASES",
    "TARGET_RADAR_STATIC_PHASES",
    "BattleTiming",
]


class BattlePhase(str, Enum):
    """戦闘の進行フェーズ"""
    INITIAL_SETUP = "initial_setup"              # 開戦前の初期コマンド入力・待機機体解決
    IDLE = "idle"                                # ATBゲージ進行・手番待機
    INPUT = "input"                              # プレイヤーのコマンド選択中
    TARGET_INDICATION = "target_indication"      # 攻撃対象の予告表示（レーダー演出）
    ATTACK_DECLARATION = "attack_declaration"    # 行動・技の宣言メッセージ表示
    CUTIN = "cutin"                              # カットイン演出（アニメーション中）
    CUTIN_RESULT = "cutin_result"                # カットイン演出結果（ヒット/ダメージ表示）
    LOG_WAIT = "log_wait"                        # 通常行動後の結果メッセージ確認待ち
    RESULT_LOG = "result_log"                    # バトル決着メッセージ確認待ち
    GAME_OVER = "game_over"                      # 勝敗決定後のリザルトオーバーレイ
    OPENING_LOG = "opening_log"                  # 開戦口上メッセージ
    OPENING_POPUP = "opening_popup"              # 開戦演出（ロボトルファイト！）


class CutinStep(str, Enum):
    """カットイン演出のステップ（第1段階：主攻撃、第2段階：貫通）"""
    PRIMARY = "primary"
    PIERCE = "pierce"


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