"""AI 戦略ロジック"""

import random
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from core.ecs import World
from battle.mechanics.targeting import TargetingMechanics


class Strategy(ABC):
    @abstractmethod
    def decide_action(self, world: World, entity_id: int) -> Tuple[str, Optional[str]]:
        pass


class RandomStrategy(Strategy):
    def decide_action(self, world: World, entity_id: int) -> Tuple[str, Optional[str]]:
        # world を使用して生存パーツを取得
        alive_parts_hp = TargetingMechanics.get_alive_parts_hp(world, entity_id)

        # 攻撃コンポーネントを持つパーツのみ抽出して候補とする
        attack_parts = []
        entity_comps = world.try_get_entity(entity_id)
        if entity_comps and 'partlist' in entity_comps:
            for p_type in alive_parts_hp:
                part_id = entity_comps['partlist'].parts.get(p_type)
                if part_id:
                    p_comps = world.try_get_entity(part_id)
                    if p_comps and 'attack' in p_comps:
                        attack_parts.append(p_type)

        if not attack_parts:
            return "skip", None

        return "attack", random.choice(attack_parts)


class StrategyRegistry:
    _strategies = {
        "random": RandomStrategy()
    }

    @classmethod
    def get(cls, strategy_id: str) -> Strategy:
        return cls._strategies.get(strategy_id, cls._strategies["random"])
