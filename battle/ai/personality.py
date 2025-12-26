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
        
        for part in ["head", "right_arm", "left_arm"]:
            if valid_targets:
                targets[part] = random.choice(valid_targets)
            else:
                targets[part] = None
        return targets

def get_personality(personality_id: str) -> Personality:
    """IDに応じた性格インスタンスを返す（現在はrandomのみ）"""
    if personality_id == "random":
        return RandomPersonality()
    return RandomPersonality()