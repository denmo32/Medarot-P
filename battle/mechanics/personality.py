"""メダルの性格に基づくターゲット選定ロジック"""

import random
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, List
from domain.constants import TraitType, PartType
from battle.mechanics.targeting import TargetingMechanics

class Personality(ABC):
    """性格の基底クラス"""
    @abstractmethod
    def select_targets(self, state, entity_id: int) -> Dict[str, Optional[Tuple[int, str]]]:
        """
        行動選択フェーズ用：各パーツ（head, right_arm, left_arm）のターゲット(機体ID, 部位名)を決定して返す
        """
        pass

    @abstractmethod
    def select_target_part(self, state, target_eid: int) -> Optional[str]:
        """
        行動実行フェーズ用：指定されたターゲット機体の中から、性格に基づいて狙う部位を決定して返す。
        """
        pass

class RandomPersonality(Personality):
    """ランダム：各パーツが独立してランダムにターゲット（機体と部位）を選ぶ性格"""
    def select_targets(self, state, entity_id: int) -> Dict[str, Optional[Tuple[int, str]]]:
        targets = {}
        valid_enemies = TargetingMechanics.get_enemy_team_entities(state, entity_id)
        
        my_comps = state.try_get_components(entity_id, 'partlist')
        if not my_comps or not valid_enemies: return {}

        for part_type in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]:
            targets[part_type] = None
            
            p_comps = state.get_part_components(entity_id, part_type, 'attack')
            if not p_comps: continue
            
            attack_comp = p_comps['attack']
            if attack_comp.trait in TraitType.SHOOTING_TRAITS:
                target_eid = random.choice(valid_enemies)
                target_part = TargetingMechanics.get_random_alive_part(state, target_eid)
                
                if target_part:
                    targets[part_type] = (target_eid, target_part)
                
        return targets

    def select_target_part(self, state, target_eid: int) -> Optional[str]:
        """指定された機体の生存パーツからランダムに選択"""
        return TargetingMechanics.get_random_alive_part(state, target_eid)

class WeightedHPPersonality(Personality):
    """HPに基づいた重み付き選択を行う性格の基底クラス"""
    def __init__(self, reverse_sort: bool):
        self.reverse_sort = reverse_sort # True: Challenger(HP高い順), False: Assassin(HP低い順)

    def select_targets(self, state, entity_id: int) -> Dict[str, Optional[Tuple[int, str]]]:
        targets = {}
        valid_enemies = TargetingMechanics.get_enemy_team_entities(state, entity_id)
        
        my_comps = state.try_get_components(entity_id, 'partlist')
        if not my_comps: return {}

        # 敵チーム全体のパーツをリストアップしてソート
        candidates = []
        for eid in valid_enemies:
            alive_parts_hp = state.get_alive_parts_hp(eid)
            for pt, hp in alive_parts_hp.items():
                candidates.append((eid, pt, hp))
        
        if not candidates:
            return {pt: None for pt in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]}

        # HPでソート
        candidates.sort(key=lambda x: x[2], reverse=self.reverse_sort)

        for part_type in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]:
            targets[part_type] = None
            p_comps = state.get_part_components(entity_id, part_type, 'attack')
            if not p_comps: continue
            
            attack_comp = p_comps['attack']
            if attack_comp.trait in TraitType.SHOOTING_TRAITS:
                # 上位候補から重み付きランダムで選択
                top_n = candidates[:3]
                weights = [0.6, 0.3, 0.1][:len(top_n)]
                
                choice = random.choices(top_n, weights=weights, k=1)[0]
                targets[part_type] = (choice[0], choice[1])
        
        return targets

    def select_target_part(self, state, target_eid: int) -> Optional[str]:
        """指定された機体の中で、HP基準で部位を選択"""
        alive_parts_hp = state.get_alive_parts_hp(target_eid)
        if not alive_parts_hp: return None
        
        # HPでソート (reverse_sort=TrueならHP高い順、Falseなら低い順)
        candidates = sorted(alive_parts_hp.items(), key=lambda x: x[1], reverse=self.reverse_sort)
        
        # 上位3つから重み付き選択
        top_n = candidates[:3]
        weights = [0.6, 0.3, 0.1][:len(top_n)]
        
        choice = random.choices(top_n, weights=weights, k=1)[0]
        return choice[0]

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