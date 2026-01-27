"""ターゲット選定と有効性判定のドメインロジック"""

import random
from typing import List, Optional, Tuple
from battle.constants import TeamType, PartType

class TargetingLogic:
    """ターゲットの状態判定や取得に関するステートレスなロジック"""

    @staticmethod
    def is_entity_alive(world, entity_id: int) -> bool:
        """エンティティが存在し、機能停止していないか確認"""
        comps = world.try_get_entity(entity_id)
        if not comps:
            return False
        if 'defeated' in comps and comps['defeated'].is_defeated:
            return False
        return True

    @staticmethod
    def is_part_alive(world, entity_id: int, part_type: str) -> bool:
        """指定した部位が生存しているか確認"""
        if not TargetingLogic.is_entity_alive(world, entity_id):
            return False
        
        comps = world.try_get_entity(entity_id)
        part_id = comps['partlist'].parts.get(part_type)
        if part_id is None:
            return False
            
        p_comps = world.try_get_entity(part_id)
        return p_comps and p_comps['health'].hp > 0

    @staticmethod
    def is_action_target_valid(world, target_id: Optional[int], target_part: Optional[str] = None) -> bool:
        """
        アクションのターゲット（機体および部位）が攻撃可能な状態か判定する。
        """
        if target_id is None: 
            return False
        if not TargetingLogic.is_entity_alive(world, target_id): 
            return False
        if target_part:
            return TargetingLogic.is_part_alive(world, target_id, target_part)
        return True

    @staticmethod
    def get_alive_parts(world, entity_id: int) -> List[str]:
        """生存しているパーツ種別のリストを取得"""
        comps = world.try_get_entity(entity_id)
        if not comps:
            return []
        
        alive_parts = []
        for pt, pid in comps['partlist'].parts.items():
            p_comps = world.try_get_entity(pid)
            if p_comps and p_comps['health'].hp > 0:
                alive_parts.append(pt)
        return alive_parts

    @staticmethod
    def get_enemy_team_entities(world, my_entity_id: int) -> List[int]:
        """敵対チームの生存しているエンティティIDリストを取得"""
        my_comps = world.try_get_entity(my_entity_id)
        if not my_comps:
            return []
        
        my_team = my_comps['team'].team_type
        target_team_type = TeamType.ENEMY if my_team == TeamType.PLAYER else TeamType.PLAYER
        
        valid_targets = []
        for eid, comps in world.get_entities_with_components('team', 'defeated'):
            if comps['team'].team_type == target_team_type and not comps['defeated'].is_defeated:
                valid_targets.append(eid)
        return valid_targets

    @staticmethod
    def get_random_alive_part(world, entity_id: int) -> Optional[str]:
        """生存パーツからランダムに1つ選択"""
        alive_parts = TargetingLogic.get_alive_parts(world, entity_id)
        return random.choice(alive_parts) if alive_parts else None