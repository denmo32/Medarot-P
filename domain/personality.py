"""メダルの性格に基づくターゲット選定ロジック"""

import random
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, List
from domain.constants import TraitType, PartType

class Personality(ABC):
    """性格の基底クラス"""
    
    @abstractmethod
    def select_targets(
        self,
        valid_enemy_ids: List[int],
        has_shooting_trait: Dict[str, bool],
        enemy_parts: Dict[int, Dict[str, int]]
    ) -> Dict[str, Optional[Tuple[int, str]]]:
        """
        行動選択フェーズ用：各パーツ（head, right_arm, left_arm）のターゲット (機体 ID, 部位名) を決定して返す
        
        Args:
            valid_enemy_ids: 生存している敵機体の ID リスト
            has_shooting_trait: パーツ種別ごとの射撃特性フラグ {part_type: bool}
            enemy_parts: 敵ごとの生存パーツと HP {enemy_id: {part_type: hp}}
        
        Returns:
            各パーツのターゲット {part_type: (target_id, target_part)}
        """
        pass

    @abstractmethod
    def select_target_part(self, alive_parts_hp: Dict[str, int]) -> Optional[str]:
        """
        行動実行フェーズ用：指定されたターゲット機体の中から、性格に基づいて狙う部位を決定して返す。
        
        Args:
            alive_parts_hp: 生存しているパーツと HP {part_type: hp}
        
        Returns:
            選択された部位種別
        """
        pass

class RandomPersonality(Personality):
    """ランダム：各パーツが独立してランダムにターゲット（機体と部位）を選ぶ性格"""
    
    def select_targets(
        self,
        valid_enemy_ids: List[int],
        has_shooting_trait: Dict[str, bool],
        enemy_parts: Dict[int, Dict[str, int]]
    ) -> Dict[str, Optional[Tuple[int, str]]]:
        targets = {}
        
        if not valid_enemy_ids or not has_shooting_trait:
            return {pt: None for pt in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]}

        for part_type in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]:
            targets[part_type] = None

            if not has_shooting_trait.get(part_type, False):
                continue
            
            # 射撃特性を持つパーツのみターゲット選択
            target_eid = random.choice(valid_enemy_ids)
            target_part_hp = enemy_parts.get(target_eid, {})
            if target_part_hp:
                target_part = random.choice(list(target_part_hp.keys()))
                targets[part_type] = (target_eid, target_part)

        return targets

    def select_target_part(self, alive_parts_hp: Dict[str, int]) -> Optional[str]:
        """指定された機体の生存パーツからランダムに選択"""
        if not alive_parts_hp:
            return None
        return random.choice(list(alive_parts_hp.keys()))

class WeightedHPPersonality(Personality):
    """HP に基づいた重み付き選択を行う性格の基底クラス"""
    
    def __init__(self, reverse_sort: bool):
        self.reverse_sort = reverse_sort  # True: Challenger(HP 高い順), False: Assassin(HP 低い順)

    def select_targets(
        self,
        valid_enemy_ids: List[int],
        has_shooting_trait: Dict[str, bool],
        enemy_parts: Dict[int, Dict[str, int]]
    ) -> Dict[str, Optional[Tuple[int, str]]]:
        targets = {}
        
        if not valid_enemy_ids or not has_shooting_trait:
            return {pt: None for pt in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]}

        # 敵チーム全体のパーツをリストアップしてソート
        candidates = []
        for eid in valid_enemy_ids:
            parts_hp = enemy_parts.get(eid, {})
            for pt, hp in parts_hp.items():
                candidates.append((eid, pt, hp))

        if not candidates:
            return {pt: None for pt in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]}

        # HP でソート
        candidates.sort(key=lambda x: x[2], reverse=self.reverse_sort)

        for part_type in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]:
            targets[part_type] = None
            
            if not has_shooting_trait.get(part_type, False):
                continue

            # 上位候補から重み付きランダムで選択
            top_n = candidates[:3]
            weights = [0.6, 0.3, 0.1][:len(top_n)]

            choice = random.choices(top_n, weights=weights, k=1)[0]
            targets[part_type] = (choice[0], choice[1])

        return targets

    def select_target_part(self, alive_parts_hp: Dict[str, int]) -> Optional[str]:
        """指定された機体の中で、HP 基準で部位を選択"""
        if not alive_parts_hp:
            return None

        # HP でソート (reverse_sort=True なら HP 高い順、False なら低い順)
        candidates = sorted(alive_parts_hp.items(), key=lambda x: x[1], reverse=self.reverse_sort)

        # 上位 3 つから重み付き選択
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
