"""AI 戦略と性格の純粋ロジック"""

import random
from abc import ABC, abstractmethod
from typing import Tuple, Optional, List, Dict
from domain.constants import PartType

# --- Strategies (from ai.py) ---

class Strategy(ABC):
    @abstractmethod
    def decide_action(self, attackable_parts: List[str]) -> Tuple[str, Optional[str]]:
        pass

class RandomStrategy(Strategy):
    def decide_action(self, attackable_parts: List[str]) -> Tuple[str, Optional[str]]:
        if not attackable_parts:
            return "skip", None
        return "attack", random.choice(attackable_parts)

_strategies = {
    "random": RandomStrategy()
}

def get_strategy(strategy_id: str) -> Strategy:
    return _strategies.get(strategy_id, _strategies["random"])


# --- Personalities (from personality.py) ---

class Personality(ABC):
    """性格の基底クラス"""
    
    @abstractmethod
    def select_targets(
        self,
        valid_enemy_ids: List[int],
        has_shooting_trait: Dict[str, bool],
        enemy_parts: Dict[int, Dict[str, int]]
    ) -> Dict[str, Optional[Tuple[int, str]]]:
        """各パーツのターゲットを決定して返す"""
        pass

    @abstractmethod
    def select_target_part(self, alive_parts_hp: Dict[str, int]) -> Optional[str]:
        """狙う部位を決定して返す"""
        pass

class RandomPersonality(Personality):
    def select_targets(
        self,
        valid_enemy_ids: List[int],
        has_shooting_trait: Dict[str, bool],
        enemy_parts: Dict[int, Dict[str, int]]
    ) -> Dict[str, Optional[Tuple[int, str]]]:
        targets = {}
        target_parts = [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]
        
        if not valid_enemy_ids or not has_shooting_trait:
            return {pt: None for pt in target_parts}

        for part_type in target_parts:
            targets[part_type] = None
            if not has_shooting_trait.get(part_type, False):
                continue
            
            target_eid = random.choice(valid_enemy_ids)
            target_part_hp = enemy_parts.get(target_eid, {})
            if target_part_hp:
                target_part = random.choice(list(target_part_hp.keys()))
                targets[part_type] = (target_eid, target_part)
        return targets

    def select_target_part(self, alive_parts_hp: Dict[str, int]) -> Optional[str]:
        if not alive_parts_hp: return None
        return random.choice(list(alive_parts_hp.keys()))

class WeightedHPPersonality(Personality):
    def __init__(self, reverse_sort: bool):
        self.reverse_sort = reverse_sort

    def select_targets(
        self,
        valid_enemy_ids: List[int],
        has_shooting_trait: Dict[str, bool],
        enemy_parts: Dict[int, Dict[str, int]]
    ) -> Dict[str, Optional[Tuple[int, str]]]:
        target_parts = [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]
        if not valid_enemy_ids or not has_shooting_trait:
            return {pt: None for pt in target_parts}

        candidates = []
        for eid in valid_enemy_ids:
            parts_hp = enemy_parts.get(eid, {})
            for pt, hp in parts_hp.items():
                candidates.append((eid, pt, hp))

        if not candidates:
            return {pt: None for pt in target_parts}

        candidates.sort(key=lambda x: x[2], reverse=self.reverse_sort)

        targets = {}
        for part_type in target_parts:
            targets[part_type] = None
            if not has_shooting_trait.get(part_type, False):
                continue

            top_n = candidates[:3]
            weights = [0.6, 0.3, 0.1][:len(top_n)]
            choice = random.choices(top_n, weights=weights, k=1)[0]
            targets[part_type] = (choice[0], choice[1])
        return targets

    def select_target_part(self, alive_parts_hp: Dict[str, int]) -> Optional[str]:
        if not alive_parts_hp: return None
        candidates = sorted(alive_parts_hp.items(), key=lambda x: x[1], reverse=self.reverse_sort)
        top_n = candidates[:3]
        weights = [0.6, 0.3, 0.1][:len(top_n)]
        choice = random.choices(top_n, weights=weights, k=1)[0]
        return choice[0]

class ChallengerPersonality(WeightedHPPersonality):
    def __init__(self): super().__init__(reverse_sort=True)

class AssassinPersonality(WeightedHPPersonality):
    def __init__(self): super().__init__(reverse_sort=False)

_personalities = {
    "challenger": ChallengerPersonality(),
    "assassin": AssassinPersonality(),
    "random": RandomPersonality()
}

def get_personality(personality_id: str) -> Personality:
    return _personalities.get(personality_id, _personalities["random"])
