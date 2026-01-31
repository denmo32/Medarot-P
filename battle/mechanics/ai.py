"""AI戦略ロジック"""

import random
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from battle.mechanics.targeting import TargetingMechanics

class Strategy(ABC):
    @abstractmethod
    def decide_action(self, world, entity_id: int) -> Tuple[str, Optional[str]]:
        pass

class RandomStrategy(Strategy):
    def decide_action(self, world, entity_id: int) -> Tuple[str, Optional[str]]:
        # TargetingMechanicsを使用して生存パーツを取得
        available_parts = TargetingMechanics.get_alive_parts(world, entity_id)
        
        # 攻撃コンポーネントを持つパーツのみ抽出して候補とする
        attack_parts = []
        comps = world.try_get_entity(entity_id)
        part_list = comps.get('partlist')
        
        if part_list:
            for p_type in available_parts:
                p_id = part_list.parts.get(p_type)
                p_comps = world.try_get_entity(p_id)
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