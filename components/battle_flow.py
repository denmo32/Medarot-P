"""バトル進行状態（フロー）を管理するコンポーネント"""

from core.ecs import Component

class BattleFlowComponent(Component):
    """バトルの現在のフェーズを管理する"""
    
    # フェーズ定義
    PHASE_IDLE = "idle"             # 通常状態（ゲージ進行、ターン待機）
    PHASE_INPUT = "input"           # コマンド入力待ち
    PHASE_EXECUTING = "executing"   # 行動処理中（リアクション判定、演出、解決）
    PHASE_LOG_WAIT = "log_wait"     # メッセージ送り待ち
    PHASE_GAME_OVER = "game_over"   # ゲーム終了

    def __init__(self):
        self.current_phase = self.PHASE_IDLE
        self.processing_event_id = None # 現在処理中のActionEventエンティティID
        self.winner = None              # 勝者（game_over時）