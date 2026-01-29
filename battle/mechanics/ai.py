"""AI戦略ロジック"""

import random
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from battle.constants import PartType
from battle.mechanics.targeting import TargetingMechanics

class Strategy(ABC):
    @abstractmethod
    def decide_action(self, world, entity_id: int) -> Tuple[str, Optional[str]]:
        pass

class RandomStrategy(Strategy):
    def decide_action(self, world, entity_id: int) -> Tuple[str, Optional[str]]:
        available_parts = []
        for part_type in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]:
            if TargetingMechanics.is_part_alive(world, entity_id, part_type):
                available_parts.append(part_type)
        
        if not available_parts:
            return "skip", None
            
        return "attack", random.choice(available_parts)

class StrategyRegistry:
    _strategies = {
        "random": RandomStrategy()
    }
    
    @classmethod
    def get(cls, strategy_id: str) -> Strategy:
        return cls._strategies.get(strategy_id, cls._strategies["random"])