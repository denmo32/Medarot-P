"""メダルの性格に基づくターゲット選定ロジック"""

import random
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, List
from domain.constants import TraitType, PartType
from battle.mechanics.targeting import TargetingMechanics

class Personality(ABC):
    """性格の基底クラス"""
    @abstractmethod
    def select_targets(self, world, entity_id: int) -> Dict[str, Optional[Tuple[int, str]]]:
        """
        行動選択フェーズ用：各パーツ（head, right_arm, left_arm）のターゲット(機体ID, 部位名)を決定して返す
        射撃攻撃などの「事前にターゲットを決める」アクションで使用。
        """
        pass

    @abstractmethod
    def select_target_part(self, world, target_eid: int) -> Optional[str]:
        """
        行動実行フェーズ用：指定されたターゲット機体の中から、性格に基づいて狙う部位を決定して返す。
        格闘攻撃などの「実行時にターゲット機体が決まる」アクションで使用。
        """
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

    def select_target_part(self, world, target_eid: int) -> Optional[str]:
        """指定された機体の生存パーツからランダムに選択"""
        return TargetingMechanics.get_random_alive_part(world, target_eid)

class WeightedHPPersonality(Personality):
    """HPに基づいた重み付き選択を行う性格の基底クラス"""
    def __init__(self, reverse_sort: bool):
        self.reverse_sort = reverse_sort # True: Challenger(HP高い順), False: Assassin(HP低い順)

    def select_targets(self, world, entity_id: int) -> Dict[str, Optional[Tuple[int, str]]]:
        targets = {}
        valid_enemies = TargetingMechanics.get_enemy_team_entities(world, entity_id)
        
        my_comps = world.try_get_entity(entity_id)
        part_list = my_comps.get('partlist')
        if not part_list: return {}

        # 敵チーム全体のパーツをリストアップしてソート
        candidates = []
        for eid in valid_enemies:
            t_comps = world.try_get_entity(eid)
            for pt, pid in t_comps['partlist'].parts.items():
                hp = world.entities[pid]['health'].hp
                if hp > 0:
                    candidates.append((eid, pt, hp))
        
        if not candidates:
            return {pt: None for pt in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]}

        # HPでソート
        candidates.sort(key=lambda x: x[2], reverse=self.reverse_sort)

        for part_type in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]:
            targets[part_type] = None
            p_id = part_list.parts.get(part_type)
            if not p_id: continue
            
            p_comps = world.try_get_entity(p_id)
            attack_comp = p_comps.get('attack') if p_comps else None
            
            if attack_comp and attack_comp.trait in TraitType.SHOOTING_TRAITS:
                # 上位候補から重み付きランダムで選択
                top_n = candidates[:3]
                weights = [0.6, 0.3, 0.1][:len(top_n)]
                
                choice = random.choices(top_n, weights=weights, k=1)[0]
                targets[part_type] = (choice[0], choice[1])
        
        return targets

    def select_target_part(self, world, target_eid: int) -> Optional[str]:
        """指定された機体の中で、HP基準で部位を選択"""
        t_comps = world.try_get_entity(target_eid)
        if not t_comps or 'partlist' not in t_comps: return None
        
        # ターゲット機体の生存パーツとHPをリストアップ
        candidates: List[Tuple[str, int]] = []
        for pt, pid in t_comps['partlist'].parts.items():
            hp_comp = world.try_get_entity(pid).get('health')
            if hp_comp and hp_comp.hp > 0:
                candidates.append((pt, hp_comp.hp))
        
        if not candidates: return None

        # HPでソート (reverse_sort=TrueならHP高い順、Falseなら低い順)
        candidates.sort(key=lambda x: x[1], reverse=self.reverse_sort)
        
        # 上位3つから重み付き選択（例: 一番条件に合うパーツを選ぶ確率が高い）
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