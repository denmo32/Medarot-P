"""ターゲット選定ロジック（旧 TargetingService）"""

import random
from typing import List, Optional, Tuple
from domain.constants import TeamType, ActionType, TraitType
from domain.gauge_logic import calculate_gauge_ratio

class TargetingMechanics:
    @staticmethod
    def is_entity_alive(world, entity_id: int) -> bool:
        comps = world.try_get_entity(entity_id)
        if not comps: return False
        if 'defeated' in comps and comps['defeated'].is_defeated: return False
        return True

    @staticmethod
    def is_part_alive(world, entity_id: int, part_type: str) -> bool:
        if not TargetingMechanics.is_entity_alive(world, entity_id): return False
        comps = world.try_get_entity(entity_id)
        part_id = comps['partlist'].parts.get(part_type)
        if part_id is None: return False
        p_comps = world.try_get_entity(part_id)
        return p_comps and p_comps['health'].hp > 0

    @staticmethod
    def is_action_target_valid(world, target_id: Optional[int], target_part: Optional[str] = None) -> bool:
        if target_id is None: return False
        if not TargetingMechanics.is_entity_alive(world, target_id): return False
        if target_part:
            return TargetingMechanics.is_part_alive(world, target_id, target_part)
        return True

    @staticmethod
    def get_alive_parts(world, entity_id: int) -> List[str]:
        comps = world.try_get_entity(entity_id)
        if not comps: return []
        alive_parts = []
        for pt, pid in comps['partlist'].parts.items():
            p_comps = world.try_get_entity(pid)
            if p_comps and p_comps['health'].hp > 0:
                alive_parts.append(pt)
        return alive_parts

    @staticmethod
    def get_enemy_team_entities(world, my_entity_id: int) -> List[int]:
        my_comps = world.try_get_entity(my_entity_id)
        if not my_comps: return []
        my_team = my_comps['team'].team_type
        target_team_type = TeamType.ENEMY if my_team == TeamType.PLAYER else TeamType.PLAYER
        valid_targets = []
        for eid, comps in world.get_entities_with_components('team', 'defeated'):
            if comps['team'].team_type == target_team_type and not comps['defeated'].is_defeated:
                valid_targets.append(eid)
        return valid_targets

    @staticmethod
    def get_random_alive_part(world, entity_id: int) -> Optional[str]:
        alive_parts = TargetingMechanics.get_alive_parts(world, entity_id)
        return random.choice(alive_parts) if alive_parts else None

    @staticmethod
    def get_closest_target_by_gauge(world, my_team_type: str):
        target_team = TeamType.ENEMY if my_team_type == TeamType.PLAYER else TeamType.PLAYER
        best_target = None
        max_ratio = float('-inf')
        for teid, tcomps in world.get_entities_with_components('team', 'defeated', 'gauge'):
            if tcomps['team'].team_type == target_team and not tcomps['defeated'].is_defeated:
                ratio = calculate_gauge_ratio(tcomps['gauge'].status, tcomps['gauge'].progress)
                if ratio > max_ratio:
                    max_ratio = ratio
                    best_target = teid
        return best_target

    @staticmethod
    def resolve_action_target(world, actor_eid: int, actor_comps, gauge) -> Tuple[Optional[int], Optional[str]]:
        if gauge.selected_action != ActionType.ATTACK or not gauge.selected_part:
            return None, None

        part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
        p_comps = world.try_get_entity(part_id) if part_id else None
        if not p_comps or 'attack' not in p_comps: return None, None

        attack_comp = p_comps['attack']
        if attack_comp.trait in TraitType.MELEE_TRAITS:
            target_id = TargetingMechanics.get_closest_target_by_gauge(world, actor_comps['team'].team_type)
            target_part = TargetingMechanics.get_random_alive_part(world, target_id) if target_id else None
            return target_id, target_part
        else:
            target_data = gauge.part_targets.get(gauge.selected_part)
            if target_data:
                tid, tpart = target_data
                if TargetingMechanics.is_action_target_valid(world, tid, tpart):
                    return tid, tpart
        return None, None