# features/battle/simulation/execution/targeting_resolver.py
"""バトルのターゲティングロジックを集約するクラス。"""
from typing import Callable, Dict, Optional, Tuple, TYPE_CHECKING

from domain.ai_logic import get_personality
from domain.constants import PartType, TargetRule
from domain.targeting import select_closest_enemy

if TYPE_CHECKING:
    from ..entities.commands import PartCommand
    from ..entities.part import Part
    from ..entities.robot import Robot
    from ..manager import BattleManager

TargetSelection = Tuple[Optional["Robot"], Optional[PartType]]
Selector = Callable[["Robot", PartType], TargetSelection]


class TargetingResolver:
    """ターゲット選定および事前予約ターゲットの有効性検証を一元管理する"""

    def __init__(self, manager: 'BattleManager'):
        self.manager = manager
        self._selectors: Dict[TargetRule, Selector] = {
            TargetRule.ENEMY_BY_PERSONALITY: self.select_auto_target,
            TargetRule.CLOSEST_ENEMY: lambda actor, _: self.select_melee_target(actor),
            TargetRule.ENEMY_RANDOM: lambda actor, _: (self._select_enemy_random(actor), None),
            TargetRule.FRIEND_LEAST_HP: lambda actor, _: (self._select_friend_least_hp(actor), None),
            TargetRule.FRIEND_ANY_BROKEN: lambda actor, _: (self._select_friend_any_broken(actor), None),
            TargetRule.SELF: lambda actor, _: (actor, None),
        }

    def resolve_target(
        self,
        actor: 'Robot',
        part: 'Part',
        existing_target: Optional['Robot'] = None,
        existing_part: Optional[PartType] = None,
    ) -> TargetSelection:
        if not part.can_execute:
            return None, None

        if part.locks_target and existing_target is not None:
            if actor.is_target_lost(existing_target, existing_part, part.targets_part):
                return None, None
            return existing_target, existing_part

        selector = self._selectors.get(part.target_rule)
        if not selector:
            return None, None
        return selector(actor, part.part_type)

    def resolve_preview_target(self, actor: 'Robot', part_type: PartType) -> Optional[TargetSelection]:
        part = actor.get_part(part_type)
        if not part or not part.locks_target:
            return None
        target_robot, target_part = self.resolve_target(actor, part)
        if target_robot is None:
            return None
        return target_robot, target_part

    def resolve_execution_target(self, command: 'PartCommand') -> TargetSelection:
        actor = command.actor
        part = actor.get_part(command.part_type)
        if not part:
            return None, None
        return self.resolve_target(
            actor, part, existing_target=command.target_robot, existing_part=command.target_part
        )

    def select_melee_target(self, actor: 'Robot') -> TargetSelection:
        t_idx = select_closest_enemy(actor.team, self.manager.robots)
        if t_idx is None:
            return None, None

        target_robot = self.manager.robots[t_idx]
        alive_parts = target_robot.get_target_parts_info()
        target_part = get_personality(actor.personality).select_target_part(alive_parts, rng=self.manager.rng)
        return target_robot, target_part

    def select_auto_target(self, actor: 'Robot', part_type: PartType) -> TargetSelection:
        enemies = [r for r in self.manager.robots if r.team != actor.team and r.is_alive]
        if not enemies:
            return None, None

        valid_enemy_ids = [self.manager.robots.index(e) for e in enemies]
        enemy_parts_data = {eid: self.manager.robots[eid].get_target_parts_info() for eid in valid_enemy_ids}

        res_map = get_personality(actor.personality).select_targets(
            valid_enemy_ids, enemy_parts_data, rng=self.manager.rng
        )
        res = res_map.get(part_type)
        if res:
            return self.manager.robots[res[0]], res[1]
        return None, None

    def _select_enemy_random(self, actor: 'Robot') -> Optional['Robot']:
        enemies = [r for r in self.manager.robots if r.team != actor.team and r.is_alive]
        return self.manager.rng.choice(enemies) if enemies else None

    def _select_friend_least_hp(self, actor: 'Robot') -> Optional['Robot']:
        friends = [r for r in self.manager.robots if r.team == actor.team and r.is_alive]
        return min(friends, key=lambda r: r.total_hp) if friends else None

    def _select_friend_any_broken(self, actor: 'Robot') -> Optional['Robot']:
        friends = [r for r in self.manager.robots if r.team == actor.team and r.is_alive]
        broken = [r for r in friends if r.has_broken_parts]
        return broken[0] if broken else None