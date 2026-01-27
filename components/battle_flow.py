"""バトル進行状態（フロー）を管理するコンポーネント"""

from core.ecs import Component
from battle.constants import BattlePhase

class BattleFlowComponent(Component):
    """バトルの現在のフェーズを管理する"""
    
    def __init__(self):
        self.current_phase = BattlePhase.IDLE
        self.processing_event_id = None # 現在処理中のActionEventエンティティID
        self.active_actor_id = None     # 現在アクション実行中（またはログ表示中）の機体ID
        self.winner = None              # 勝者（game_over時）
        self.phase_timer = 0.0          # フェーズ遷移待ち用タイマー
        self.cutin_progress = 0.0       # カットイン演出進行度(0.0~1.0)
        self.target_line_offset = 0.0   # ターゲットラインのアニメーション用オフセット