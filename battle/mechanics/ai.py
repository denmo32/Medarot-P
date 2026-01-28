"""AI戦略ロジック（旧 AIStrategyService）"""

import random
from abc import ABC, abstractmethod
from typing import Tuple, Optional

class Strategy(ABC):
    @abstractmethod
    def decide_action(self, world, entity_id: int) -> Tuple[str, Optional[str]]:
        pass

class RandomStrategy(Strategy):
    def decide_action(self, world, entity_id: int) -> Tuple[str, Optional[str]]:
        comps = world.entities.get(entity_id)
        part_list = comps.get('partlist')
        
        available_parts = []
        for part_type in ["head", "right_arm", "left_arm"]:
            p_id = part_list.parts.get(part_type)
            if p_id:
                h = world.entities[p_id].get('health')
                if h and h.hp > 0:
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