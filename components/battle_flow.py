"""バトル進行状態（フロー）を管理するコンポーネント"""

from core.ecs import Component
from battle.constants import BattlePhase

class BattleFlowComponent(Component):
    """バトルの現在のフェーズを管理する"""
    
    # フェーズ定義 (constantsと同様だがクラス定数として保持)
    PHASE_IDLE = BattlePhase.IDLE
    PHASE_INPUT = BattlePhase.INPUT
    PHASE_TARGET_INDICATION = BattlePhase.TARGET_INDICATION
    PHASE_EXECUTING = BattlePhase.EXECUTING
    PHASE_LOG_WAIT = BattlePhase.LOG_WAIT
    PHASE_GAME_OVER = BattlePhase.GAME_OVER

    def __init__(self):
        self.current_phase = self.PHASE_IDLE
        self.processing_event_id = None # 現在処理中のActionEventエンティティID
        self.active_actor_id = None     # 現在アクション実行中（またはログ表示中）の機体ID
        self.winner = None              # 勝者（game_over時）
        self.phase_timer = 0.0          # フェーズ遷移待ち用タイマー