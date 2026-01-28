"""バトルフロー制御ロジック（旧 FlowService）"""

from typing import Optional, Tuple
from battle.constants import BattlePhase

def get_battle_state(world) -> Tuple[Optional[any], Optional[any]]:
    entities = world.get_entities_with_components('battlecontext', 'battleflow')
    if not entities:
        return None, None
    return entities[0][1]['battlecontext'], entities[0][1]['battleflow']

def transition_to_phase(flow, next_phase: str, timer: float = 0.0):
    flow.current_phase = next_phase
    flow.phase_timer = timer
    if next_phase == BattlePhase.IDLE:
        flow.processing_event_id = None
        flow.active_actor_id = None
        flow.cutin_progress = 0.0