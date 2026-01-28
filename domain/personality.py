"""メダルの性格に基づくターゲット選定ロジック"""

import random
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Tuple
from domain.constants import TraitType, PartType
from battle.mechanics.targeting import TargetingMechanics

class Personality(ABC):
    """性格の基底クラス"""
    @abstractmethod
    def select_targets(self, world, entity_id: int) -> Dict[str, Optional[Tuple[int, str]]]:
        """各パーツ（head, right_arm, left_arm）のターゲット(機体ID, 部位名)を決定して返す"""
        pass

class RandomPersonality(Personality):
    """ランダム：各パーツが独立してランダムにターゲット（機体と部位）を選ぶ性格"""
    def select_targets(self, world, entity_id: int) -> Dict[str, Optional[Tuple[int, str]]]:
        targets = {}
        valid_enemies = TargetingMechanics.get_enemy_team_entities(world, entity_id)
        
        my_comps = world.try_get_entity(entity_id)
        part_list = my_comps.get('partlist')
        if not part_list or not valid_enemies: return {}

        for part_type in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]:
            targets[part_type] = None
            
            p_id = part_list.parts.get(part_type)
            if not p_id: continue
            
            p_comps = world.try_get_entity(p_id)
            attack_comp = p_comps.get('attack') if p_comps else None
            
            if not attack_comp: continue

            if attack_comp.trait in TraitType.SHOOTING_TRAITS:
                target_eid = random.choice(valid_enemies)
                target_part = TargetingMechanics.get_random_alive_part(world, target_eid)
                
                if target_part:
                    targets[part_type] = (target_eid, target_part)
                
        return targets

class WeightedHPPersonality(Personality):
    """HPに基づいた重み付き選択を行う性格の基底クラス"""
    def __init__(self, reverse_sort: bool):
        self.reverse_sort = reverse_sort

    def select_targets(self, world, entity_id: int) -> Dict[str, Optional[Tuple[int, str]]]:
        targets = {}
        valid_enemies = TargetingMechanics.get_enemy_team_entities(world, entity_id)
        
        my_comps = world.try_get_entity(entity_id)
        part_list = my_comps.get('partlist')
        if not part_list: return {}

        candidates = []
        for eid in valid_enemies:
            t_comps = world.try_get_entity(eid)
            for pt, pid in t_comps['partlist'].parts.items():
                hp = world.entities[pid]['health'].hp
                if hp > 0:
                    candidates.append((eid, pt, hp))
        
        if not candidates:
            return {pt: None for pt in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]}

        candidates.sort(key=lambda x: x[2], reverse=self.reverse_sort)

        for part_type in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]:
            targets[part_type] = None
            p_id = part_list.parts.get(part_type)
            if not p_id: continue
            
            p_comps = world.try_get_entity(p_id)
            attack_comp = p_comps.get('attack') if p_comps else None
            
            if attack_comp and attack_comp.trait in TraitType.SHOOTING_TRAITS:
                top_n = candidates[:3]
                weights = [0.6, 0.3, 0.1][:len(top_n)]
                
                choice = random.choices(top_n, weights=weights, k=1)[0]
                targets[part_type] = (choice[0], choice[1])
        
        return targets

class ChallengerPersonality(WeightedHPPersonality):
    def __init__(self):
        super().__init__(reverse_sort=True)

class AssassinPersonality(WeightedHPPersonality):
    def __init__(self):
        super().__init__(reverse_sort=False)

class PersonalityRegistry:
    _personalities = {
        "challenger": ChallengerPersonality(),
        "assassin": AssassinPersonality(),
        "random": RandomPersonality()
    }
    
    @classmethod
    def get(cls, personality_id: str) -> Personality:
        return cls._personalities.get(personality_id, cls._personalities["random"])