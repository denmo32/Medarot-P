"""バトルフロー制御に関連するサービス"""

from typing import Optional, Tuple
from battle.constants import BattlePhase

def get_battle_state(world) -> Tuple[Optional[any], Optional[any]]:
    """バトル全体の共通コンポーネント(context, flow)を安全に取得する"""
    entities = world.get_entities_with_components('battlecontext', 'battleflow')
    if not entities:
        return None, None
    return entities[0][1]['battlecontext'], entities[0][1]['battleflow']

def transition_to_phase(flow, next_phase: str, timer: float = 0.0):
    """バトルフェーズを遷移させ、タイマー等の関連状態を初期化する"""
    flow.current_phase = next_phase
    flow.phase_timer = timer
    if next_phase == BattlePhase.IDLE:
        flow.processing_event_id = None
        flow.active_actor_id = None
        flow.cutin_progress = 0.0
