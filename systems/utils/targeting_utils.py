"""ECS ワールド操作を必要とするターゲット関連ユーティリティ"""

from typing import Dict, Optional
from core.ecs import World


class TargetingUtils:
    """
    ECS ワールド操作を必要とするターゲット関連ユーティリティ
    
    これらの関数は World インスタンスへのアクセスが必要なため、
    システム層でのみ使用することを想定しています。
    """

    @staticmethod
    def is_part_alive(world: World, entity_id: int, part_type: str) -> bool:
        """指定部位が生存しているか（機体が機能停止していないことも含む）"""
        entity_comps = world.try_get_entity(entity_id)
        if not entity_comps:
            return False
        
        defeated = entity_comps.get('defeated')
        if defeated and defeated.is_defeated:
            return False
        
        parts = entity_comps.get('partlist')
        if not parts:
            return False
        
        pid = parts.parts.get(part_type)
        if pid is None:
            return False
        
        p_comps = world.try_get_entity(pid)
        return bool(p_comps and 'health' in p_comps and p_comps['health'].hp > 0)

    @staticmethod
    def get_alive_parts_hp(world: World, entity_id: int) -> Dict[str, int]:
        """生存している部位名とその HP の辞書を取得"""
        entity_comps = world.try_get_entity(entity_id)
        if not entity_comps or 'partlist' not in entity_comps:
            return {}

        result = {}
        for pt, pid in entity_comps['partlist'].parts.items():
            p_comps = world.try_get_entity(pid)
            if p_comps and 'health' in p_comps:
                hp = p_comps['health'].hp
                if hp > 0:
                    result[pt] = hp
        return result
