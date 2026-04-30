"""バトルフローの ECS 操作用ユーティリティ"""

from typing import Optional, Tuple, Dict, Any
from core.ecs import World

def get_battle_state(world: World) -> Tuple[Optional[Any], Optional[Any]]:
    """ワールドから BattleContext と BattleFlow を取得する。"""
    _, comps = world.get_first_entity('battlecontext', 'battleflow')
    if not comps:
        return None, None
    return comps['battlecontext'], comps['battleflow']

def manage_queue(context: Any, entity_id: int, should_add: bool) -> None:
    """待機列への追加・削除"""
    if not context:
        return
    queue = context.waiting_queue
    if should_add and entity_id not in queue:
        queue.append(entity_id)
    elif not should_add and entity_id in queue:
        queue.remove(entity_id)
