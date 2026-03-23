"""AI戦略ロジック"""

import random
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from battle.mechanics.targeting import TargetingMechanics

class Strategy(ABC):
    @abstractmethod
    def decide_action(self, state, entity_id: int) -> Tuple[str, Optional[str]]:
        pass

class RandomStrategy(Strategy):
    def decide_action(self, state, entity_id: int) -> Tuple[str, Optional[str]]:
        # state を使用して生存パーツを取得
        alive_parts_hp = state.get_alive_parts_hp(entity_id)
        
        # 攻撃コンポーネントを持つパーツのみ抽出して候補とする
        attack_parts = []
        for p_type in alive_parts_hp:
            p_comps = state.get_part_components(entity_id, p_type, 'attack')
            if p_comps:
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