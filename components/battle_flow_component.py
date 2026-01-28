"""バトル進行状態（フロー）を管理するコンポーネント"""

from dataclasses import dataclass, field
from typing import Optional
from core.ecs import Component
from battle.constants import BattlePhase

@dataclass
class BattleFlowComponent(Component):
    """バトルの現在のフェーズを管理する"""
    current_phase: str = BattlePhase.IDLE
    processing_event_id: Optional[int] = None # 現在処理中のActionEventエンティティID
    active_actor_id: Optional[int] = None     # 現在アクション実行中（またはログ表示中）の機体ID
    winner: Optional[str] = None              # 勝者（game_over時）
    phase_timer: float = 0.0                  # フェーズ遷移待ち用タイマー
    cutin_progress: float = 0.0               # カットイン演出進行度(0.0~1.0)
    target_line_offset: float = 0.0           # ターゲットラインのアニメーション用オフセット