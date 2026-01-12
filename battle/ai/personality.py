"""メダルの性格に基づくターゲット選定ロジック"""

import random
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Tuple

class Personality(ABC):
    """性格の基底クラス"""
    @abstractmethod
    def select_targets(self, world, entity_id: int) -> Dict[str, Optional[Tuple[int, str]]]:
        """各パーツ（head, right_arm, left_arm）のターゲット(機体ID, 部位名)を決定して返す"""
        pass

    def _get_valid_targets(self, world, my_entity_id: int) -> List[int]:
        """攻撃可能な敵対エンティティIDのリストを取得"""
        my_comps = world.entities.get(my_entity_id)
        if not my_comps: return []
        
        my_team = my_comps.get('team').team_type
        target_team_type = "enemy" if my_team == "player" else "player"
        
        valid_targets = []
        for eid, comps in world.get_entities_with_components('team', 'defeated'):
            if comps['team'].team_type == target_team_type and not comps['defeated'].is_defeated:
                valid_targets.append(eid)
        return valid_targets

class RandomPersonality(Personality):
    """ランダム：各パーツが独立してランダムにターゲット（機体と部位）を選ぶ性格"""
    def select_targets(self, world, entity_id: int) -> Dict[str, Optional[Tuple[int, str]]]:
        targets = {}
        valid_targets = self._get_valid_targets(world, entity_id)
        
        my_comps = world.entities.get(entity_id)
        part_list = my_comps.get('partlist')
        if not part_list: return {}

        for part_type in ["head", "right_arm", "left_arm"]:
            targets[part_type] = None
            
            p_id = part_list.parts.get(part_type)
            if not p_id or not valid_targets:
                continue
            
            # パーツの特性（trait）を確認
            p_comps = world.entities.get(p_id)
            attack_comp = p_comps.get('attack') if p_comps else None
            
            if attack_comp:
                # 事前ターゲット武器（ライフル・ガトリング）の場合のみ、事前に選定
                if attack_comp.trait in ["ライフル", "ガトリング"]:
                    target_eid = random.choice(valid_targets)
                    
                    # ターゲット機体の生存部位からランダムに選択
                    t_comps = world.entities.get(target_eid)
                    alive_parts = []
                    if t_comps:
                        for pt, pid in t_comps['partlist'].parts.items():
                            if world.entities[pid]['health'].hp > 0:
                                alive_parts.append(pt)
                    
                    if alive_parts:
                        targets[part_type] = (target_eid, random.choice(alive_parts))
                
                # 直前ターゲット武器（ソード・ハンマー）の場合は None のまま（実行時に決定）
                
        return targets

class WeightedHPPersonality(Personality):
    """HPに基づいた重み付き選択を行う性格の基底クラス"""
    def __init__(self, reverse_sort: bool):
        self.reverse_sort = reverse_sort

    def select_targets(self, world, entity_id: int) -> Dict[str, Optional[Tuple[int, str]]]:
        targets = {}
        valid_enemy_ids = self._get_valid_targets(world, entity_id)
        
        my_comps = world.entities.get(entity_id)
        part_list = my_comps.get('partlist')
        if not part_list: return {}

        # 全敵機体の生存パーツをリストアップ
        candidates = []
        for eid in valid_enemy_ids:
            t_comps = world.entities.get(eid)
            for pt, pid in t_comps['partlist'].parts.items():
                hp = world.entities[pid]['health'].hp
                if hp > 0:
                    candidates.append((eid, pt, hp))
        
        if not candidates:
            return {pt: None for pt in ["head", "right_arm", "left_arm"]}

        # HPでソート（reverse_sort=Trueなら降順、Falseなら昇順）
        candidates.sort(key=lambda x: x[2], reverse=self.reverse_sort)

        # 各パーツのターゲットを決定
        for part_type in ["head", "right_arm", "left_arm"]:
            targets[part_type] = None
            p_id = part_list.parts.get(part_type)
            if not p_id: continue
            
            p_comps = world.entities.get(p_id)
            attack_comp = p_comps.get('attack') if p_comps else None
            
            # 事前ターゲット武器のみ決定
            if attack_comp and attack_comp.trait in ["ライフル", "ガトリング"]:
                # 上位3つを取得し、6:3:1の確率で選択
                top_n = candidates[:3]
                weights = [0.6, 0.3, 0.1][:len(top_n)]
                
                choice = random.choices(top_n, weights=weights, k=1)[0]
                targets[part_type] = (choice[0], choice[1])
        
        return targets

class ChallengerPersonality(WeightedHPPersonality):
    """チャレンジャー：残りHPの最も高いパーツを優先"""
    def __init__(self):
        super().__init__(reverse_sort=True)

class AssassinPersonality(WeightedHPPersonality):
    """アサシン：残りHPの最も低いパーツを優先"""
    def __init__(self):
        super().__init__(reverse_sort=False)

def get_personality(personality_id: str) -> Personality:
    """IDに応じた性格インスタンスを返す"""
    if personality_id == "challenger":
        return ChallengerPersonality()
    if personality_id == "assassin":
        return AssassinPersonality()
    return RandomPersonality()