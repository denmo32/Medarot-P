"""ターゲット選定・状態確認ロジック"""

import random
from typing import List, Optional
from domain.constants import TeamType
from domain.gauge_logic import calculate_gauge_ratio

class TargetingMechanics:
    """エンティティの生存・有効性・クエリに関するユーティリティ"""

    @staticmethod
    def is_entity_alive(world, entity_id: int) -> bool:
        comps = world.try_get_entity(entity_id)
        if not comps: return False
        defeated = comps.get('defeated')
        return not defeated.is_defeated if defeated else True

    @staticmethod
    def is_part_alive(world, entity_id: int, part_type: str) -> bool:
        comps = world.try_get_components(entity_id, 'partlist')
        if not comps: return False
        
        part_id = comps['partlist'].parts.get(part_type)
        if part_id is None: return False
        
        p_comps = world.try_get_entity(part_id)
        return p_comps and p_comps['health'].hp > 0

    @staticmethod
    def is_action_target_valid(world, target_id: Optional[int], target_part: Optional[str] = None) -> bool:
        """エンティティおよび指定部位が有効（生存）か一括チェック"""
        if target_id is None: return False
        if not TargetingMechanics.is_entity_alive(world, target_id): return False
        if target_part:
            return TargetingMechanics.is_part_alive(world, target_id, target_part)
        return True

    @staticmethod
    def get_alive_parts(world, entity_id: int) -> List[str]:
        comps = world.try_get_components(entity_id, 'partlist')
        if not comps: return []
        
        return [pt for pt, pid in comps['partlist'].parts.items() 
                if world.try_get_entity(pid)['health'].hp > 0]

    @staticmethod
    def get_enemy_team_entities(world, my_entity_id: int) -> List[int]:
        my_comps = world.try_get_components(my_entity_id, 'team')
        if not my_comps: return []
        
        my_team = my_comps['team'].team_type
        target_team_type = TeamType.ENEMY if my_team == TeamType.PLAYER else TeamType.PLAYER
        
        return [eid for eid, comps in world.get_entities_with_components('team', 'defeated')
                if comps['team'].team_type == target_team_type and not comps['defeated'].is_defeated]

    @staticmethod
    def get_random_alive_part(world, entity_id: int) -> Optional[str]:
        alive_parts = TargetingMechanics.get_alive_parts(world, entity_id)
        return random.choice(alive_parts) if alive_parts else None

    @staticmethod
    def get_closest_target_by_gauge(world, my_team_type: str) -> Optional[int]:
        """最もゲージが進んでいる（中央に近い）敵を取得"""
        target_team = TeamType.ENEMY if my_team_type == TeamType.PLAYER else TeamType.PLAYER
        best_target, max_ratio = None, float('-inf')
        
        for teid, tcomps in world.get_entities_with_components('team', 'defeated', 'gauge'):
            if tcomps['team'].team_type == target_team and not tcomps['defeated'].is_defeated:
                ratio = calculate_gauge_ratio(tcomps['gauge'].status, tcomps['gauge'].progress)
                if ratio > max_ratio:
                    max_ratio, best_target = ratio, teid
        return best_target