"""ターゲット選定・状態確認ロジック（旧 TargetingService）"""

import random
from typing import List, Optional, Tuple, Dict, Any
from domain.constants import TeamType, ActionType
from domain.gauge_logic import calculate_gauge_ratio

class TargetingMechanics:
    """エンティティの生存・有効性・クエリに関するユーティリティ"""

    @staticmethod
    def get_components(world, entity_id: int, *names: str) -> Optional[Dict[str, Any]]:
        """指定した全コンポーネントを持つエンティティを取得するヘルパー"""
        comps = world.try_get_entity(entity_id)
        if not comps: return None
        if all(name in comps for name in names):
            return comps
        return None

    @staticmethod
    def is_entity_alive(world, entity_id: int) -> bool:
        comps = world.try_get_entity(entity_id)
        if not comps: return False
        defeated = comps.get('defeated')
        return not defeated.is_defeated if defeated else True

    @staticmethod
    def is_part_alive(world, entity_id: int, part_type: str) -> bool:
        comps = TargetingMechanics.get_components(world, entity_id, 'partlist')
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
        comps = TargetingMechanics.get_components(world, entity_id, 'partlist')
        if not comps: return []
        
        return [pt for pt, pid in comps['partlist'].parts.items() 
                if world.try_get_entity(pid)['health'].hp > 0]

    @staticmethod
    def get_enemy_team_entities(world, my_entity_id: int) -> List[int]:
        my_comps = TargetingMechanics.get_components(world, my_entity_id, 'team')
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

    @staticmethod
    def resolve_action_target(world, actor_eid: int, actor_comps, gauge) -> Tuple[Optional[int], Optional[str]]:
        """行動実行の瞬間に最終的なターゲットを確定させる"""
        from battle.mechanics.trait import TraitRegistry
        
        if gauge.selected_action != ActionType.ATTACK or not gauge.selected_part:
            return None, None

        # 実行パーツの有効性確認
        if not TargetingMechanics.is_part_alive(world, actor_eid, gauge.selected_part):
            return None, None

        part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
        p_comps = world.try_get_entity(part_id)
        attack_comp = p_comps.get('attack') if p_comps else None
        if not attack_comp: return None, None

        # 特性振る舞いに解決を委譲
        trait_behavior = TraitRegistry.get(attack_comp.trait)
        return trait_behavior.resolve_target(world, actor_eid, actor_comps, gauge)