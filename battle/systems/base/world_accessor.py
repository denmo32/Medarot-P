"""ECS World への共通アクセスユーティリティ"""

from typing import Optional, Tuple, Any
from core.ecs import World

def get_battle_state(world: World) -> Tuple[Optional[Any], Optional[Any]]:
    """ワールドから BattleContext と BattleFlow を取得する。"""
    _, comps = world.get_first_entity('battlecontext', 'battleflow')
    if not comps:
        return None, None
    return comps['battlecontext'], comps['battleflow']
