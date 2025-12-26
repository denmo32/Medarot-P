"""コマンダーの方針に基づく行動決定ロジック"""

import random
from abc import ABC, abstractmethod
from typing import Tuple, Optional

class Strategy(ABC):
    """コマンダーの方針（AI）の基底クラス"""
    @abstractmethod
    def decide_action(self, world, entity_id: int) -> Tuple[str, Optional[str]]:
        """(アクション名, 使用パーツ名) を決定して返す"""
        pass

class RandomStrategy(Strategy):
    """ランダム方針：使用可能な攻撃パーツからランダムに選択する"""
    def decide_action(self, world, entity_id: int) -> Tuple[str, Optional[str]]:
        comps = world.entities.get(entity_id)
        part_list = comps.get('partlist')
        
        available_parts = []
        for part_type in ["head", "right_arm", "left_arm"]:
            p_id = part_list.parts.get(part_type)
            if p_id:
                h = world.entities[p_id].get('health')
                if h and h.hp > 0:
                    available_parts.append(part_type)
        
        if not available_parts:
            return "skip", None
            
        return "attack", random.choice(available_parts)

def get_strategy(strategy_id: str) -> Strategy:
    """IDに応じた方針インスタンスを返す（現在はrandomのみ）"""
    if strategy_id == "random":
        return RandomStrategy()
    return RandomStrategy()