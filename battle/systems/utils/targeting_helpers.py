"""ターゲット解決のための ECS ヘルパー（TargetResolver パターン）"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Dict
from domain.constants import PartType, TraitType
from core.ecs import World
from domain.targeting_logic import get_closest_target_by_gauge
from domain.ai_logic import get_personality

class TargetResolver(ABC):
    """ターゲット解決のための戦略インターフェース"""
    @abstractmethod
    def resolve(
        self,
        actor_eid: int,
        selected_part: Optional[str],
        world: World
    ) -> Tuple[Optional[int], Optional[str]]:
        pass

class MeleeTargetResolver(TargetResolver):
    """格闘特性用ターゲット解決"""
    def resolve(
        self,
        actor_eid: int,
        selected_part: Optional[str],
        world: World
    ) -> Tuple[Optional[int], Optional[str]]:
        actor_comps = world.try_get_entity(actor_eid)
        if not actor_comps: return None, None

        target_team = "enemy" if actor_comps['team'].team_type == "player" else "player"

        enemy_gauge_data: List[Tuple[int, str, float]] = []
        for eid, ecomps in world.get_entities_with_components('team', 'defeated', 'gauge'):
            if ecomps['team'].team_type == target_team and not ecomps['defeated'].is_defeated:
                enemy_gauge_data.append((eid, ecomps['gauge'].status, ecomps['gauge'].progress))

        closest_enemy_id = get_closest_target_by_gauge(enemy_gauge_data)
        if not closest_enemy_id: return None, None

        personality = get_personality(actor_comps['medal'].personality_id)
        alive_parts_hp = self._get_alive_parts_hp(world, closest_enemy_id)
        if not alive_parts_hp: return None, None

        target_part = personality.select_target_part(alive_parts_hp)
        return closest_enemy_id, target_part

    def _get_alive_parts_hp(self, world: World, eid: int) -> Dict[str, int]:
        comps = world.try_get_entity(eid)
        if not comps or 'partlist' not in comps: return {}
        res = {}
        for pt, pid in comps['partlist'].parts.items():
            p_comps = world.try_get_entity(pid)
            if p_comps and 'health' in p_comps:
                hp = p_comps['health'].hp
                if hp > 0: res[pt] = hp
        return res

class RangedTargetResolver(TargetResolver):
    """射撃特性用ターゲット解決"""
    def resolve(
        self,
        actor_eid: int,
        selected_part: Optional[str],
        world: World
    ) -> Tuple[Optional[int], Optional[str]]:
        actor_comps = world.try_get_entity(actor_eid)
        if not actor_comps or 'gauge' not in actor_comps: return None, None

        gauge = actor_comps['gauge']
        target_data = gauge.part_targets.get(selected_part)

        if target_data:
            target_id, target_part = target_data
            if self._is_part_alive(world, target_id, target_part):
                return target_id, target_part
        return None, None

    def _is_part_alive(self, world: World, eid: int, part_type: str) -> bool:
        comps = world.try_get_entity(eid)
        if not comps or (comps.get('defeated') and comps['defeated'].is_defeated): return False
        pid = comps['partlist'].parts.get(part_type)
        if pid is None: return False
        p_comps = world.try_get_entity(pid)
        return bool(p_comps and 'health' in p_comps and p_comps['health'].hp > 0)

class DefaultTargetResolver(TargetResolver):
    def resolve(self, actor_eid: int, selected_part: Optional[str], world: World) -> Tuple[Optional[int], Optional[str]]:
        return None, None

class TargetResolverFactory:
    """特性に応じた TargetResolver を取得するファクトリ"""
    _resolvers = {
        "melee": MeleeTargetResolver(),
        "ranged": RangedTargetResolver(),
        "default": DefaultTargetResolver(),
    }

    @classmethod
    def get(cls, attack_trait: str) -> TargetResolver:
        if attack_trait in TraitType.MELEE_TRAITS:
            return cls._resolvers["melee"]
        elif attack_trait in TraitType.SHOOTING_TRAITS:
            return cls._resolvers["ranged"]
        return cls._resolvers["default"]
