"""ターゲット選定と有効性判定のドメインサービス"""

import random
from typing import List, Optional, Tuple
from battle.constants import TeamType, PartType, ActionType, TraitType

class TargetingService:
    """World（状態）を探索・クエリするためのサービス。ステートレス。"""

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
        if not TargetingService.is_entity_alive(world, entity_id):
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
        if not TargetingService.is_entity_alive(world, target_id): 
            return False
        if target_part:
            return TargetingService.is_part_alive(world, target_id, target_part)
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
        alive_parts = TargetingService.get_alive_parts(world, entity_id)
        return random.choice(alive_parts) if alive_parts else None

    @staticmethod
    def get_closest_target_by_gauge(world, my_team_type: str):
        """ゲージ進行度に基づいて「最も中央に近い（手前にいる）」ターゲットを選定する。"""
        from battle.domain.gauge_logic import calculate_gauge_ratio
        target_team = TeamType.ENEMY if my_team_type == TeamType.PLAYER else TeamType.PLAYER
        best_target = None
        max_ratio = float('-inf')
        
        candidates = world.get_entities_with_components('team', 'defeated', 'gauge')
        for teid, tcomps in candidates:
            if tcomps['team'].team_type == target_team and not tcomps['defeated'].is_defeated:
                ratio = calculate_gauge_ratio(tcomps['gauge'].status, tcomps['gauge'].progress)
                if ratio > max_ratio:
                    max_ratio = ratio
                    best_target = teid
        return best_target

    @staticmethod
    def resolve_action_target(world, actor_eid: int, actor_comps, gauge) -> Tuple[Optional[int], Optional[str]]:
        """
        実行しようとしているアクションに基づき、最終的なターゲット(機体ID, 部位)を解決する。
        """
        if gauge.selected_action != ActionType.ATTACK or not gauge.selected_part:
            return None, None

        part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
        p_comps = world.try_get_entity(part_id) if part_id else None
        if not p_comps or 'attack' not in p_comps:
            return None, None

        attack_comp = p_comps['attack']
        
        # 格闘特性（近接攻撃）の場合：実行時に最も近い相手を狙う
        if attack_comp.trait in TraitType.MELEE_TRAITS:
            target_id = TargetingService.get_closest_target_by_gauge(world, actor_comps['team'].team_type)
            target_part = TargetingService.get_random_alive_part(world, target_id) if target_id else None
            return target_id, target_part
        
        # 射撃特性（事前ターゲット）の場合：選定済みのターゲットが有効か確認
        else:
            target_data = gauge.part_targets.get(gauge.selected_part)
            if target_data:
                tid, tpart = target_data
                if TargetingService.is_action_target_valid(world, tid, tpart):
                    return tid, tpart
        
        return None, None