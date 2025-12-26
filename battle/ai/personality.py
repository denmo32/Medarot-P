"""メダルの性格に基づくターゲット選定ロジック"""

import random
from abc import ABC, abstractmethod
from typing import Dict, Optional, List

class Personality(ABC):
    """性格の基底クラス"""
    @abstractmethod
    def select_targets(self, world, entity_id: int) -> Dict[str, Optional[int]]:
        """各パーツ（head, right_arm, left_arm）のターゲットを決定して返す"""
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
    """ランダム：各パーツが独立してランダムにターゲットを選ぶ性格"""
    def select_targets(self, world, entity_id: int) -> Dict[str, Optional[int]]:
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
                    targets[part_type] = random.choice(valid_targets)
                # 直前ターゲット武器（ソード・ハンマー）の場合は None のまま（実行時に決定）
                
        return targets

def get_personality(personality_id: str) -> Personality:
    """IDに応じた性格インスタンスを返す（現在はrandomのみ）"""
    if personality_id == "random":
        return RandomPersonality()
    return RandomPersonality()