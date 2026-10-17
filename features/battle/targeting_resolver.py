"""バトルのターゲティングロジックを集約するクラス（RNG 注入）。"""
from typing import Callable, Dict, Optional, Tuple, TYPE_CHECKING

from domain.ai_logic import get_personality
from domain.constants import PartType, TargetRule
from domain.targeting import select_closest_enemy

if TYPE_CHECKING:
    from .context import BattleContext
    from .models import Robot

TargetSelection = Tuple[Optional["Robot"], Optional[PartType]]
Selector = Callable[["Robot", PartType], TargetSelection]


class TargetingResolver:
    def __init__(self, ctx: 'BattleContext'):
        self.ctx = ctx
        self._selectors: Dict[TargetRule, Selector] = {
            TargetRule.ENEMY_BY_PERSONALITY: self.select_auto_target,
            TargetRule.CLOSEST_ENEMY: lambda actor, _: self.select_melee_target(actor),
            TargetRule.ENEMY_RANDOM: lambda actor, _: (self._select_enemy_random(actor), None),
            TargetRule.FRIEND_LEAST_HP: lambda actor, _: (self._select_friend_least_hp(actor), None),
            TargetRule.FRIEND_ANY_BROKEN: lambda actor, _: (self._select_friend_any_broken(actor), None),
            TargetRule.SELF: lambda actor, _: (actor, None),
        }

    def resolve_preview_target(self, actor: 'Robot', part_type: PartType) -> Optional[TargetSelection]:
        part = actor.get_part(part_type)
        if not part or not part.can_execute or not part.locks_target:
            return None

        selector = self._selectors.get(part.target_rule)
        if not selector:
            return None

        robot, target_part = selector(actor, part_type)
        if robot is None:
            return None
        return robot, target_part

    def resolve_execution_target(self, actor: 'Robot', part_type: PartType) -> TargetSelection:
        command = actor.current_part_command
        if command is None:
            return None, None

        part = actor.get_part(part_type)
        if not part:
            return None, None

        if not part.locks_target:
            selector = self._selectors.get(part.target_rule)
            return selector(actor, part_type) if selector else (None, None)

        target_robot = command.target_robot
        if not target_robot or not target_robot.is_alive:
            return None, None

        target_part = command.target_part
        if part.targets_part:
            if not target_part or not target_robot.is_part_alive(target_part):
                return None, None

        return target_robot, target_part

    def select_melee_target(self, actor: 'Robot') -> TargetSelection:
        robots_data = [r.get_snapshot(i) for i, r in enumerate(self.ctx.robots)]
        t_idx = select_closest_enemy(actor.team, robots_data)
        if t_idx is None:
            return None, None

        target_robot = self.ctx.robots[t_idx]
        alive_parts = target_robot.get_target_parts_info()
        target_part = get_personality(actor.personality).select_target_part(alive_parts, rng=self.ctx.rng)
        return target_robot, target_part

    def select_auto_target(self, actor: 'Robot', part_type: PartType) -> TargetSelection:
        enemies = [r for r in self.ctx.robots if r.team != actor.team and r.is_alive]
        if not enemies:
            return None, None

        valid_enemy_ids = [self.ctx.robots.index(e) for e in enemies]
        enemy_parts_data = {eid: self.ctx.robots[eid].get_target_parts_info() for eid in valid_enemy_ids}

        res_map = get_personality(actor.personality).select_targets(
            valid_enemy_ids, enemy_parts_data, rng=self.ctx.rng
        )
        res = res_map.get(part_type)
        if res:
            return self.ctx.robots[res[0]], res[1]
        return None, None

    def _select_enemy_random(self, actor: 'Robot') -> Optional['Robot']:
        enemies = [r for r in self.ctx.robots if r.team != actor.team and r.is_alive]
        return self.ctx.rng.choice(enemies) if enemies else None

    def _select_friend_least_hp(self, actor: 'Robot') -> Optional['Robot']:
        friends = [r for r in self.ctx.robots if r.team == actor.team and r.is_alive]
        return min(friends, key=lambda r: r.total_hp) if friends else None

    def _select_friend_any_broken(self, actor: 'Robot') -> Optional['Robot']:
        friends = [r for r in self.ctx.robots if r.team == actor.team and r.is_alive]
        broken = [r for r in friends if r.has_broken_parts]
        return broken[0] if broken else None