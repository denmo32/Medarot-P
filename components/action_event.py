"""行動イベントを表すコンポーネント"""

from typing import Optional, Dict, Any
from core.ecs import Component

class ActionEventComponent(Component):
    """
    1回の行動（攻撃など）の情報を保持する。
    InitiationSystemで生成され、ResolutionSystemで解決・削除される。
    """
    def __init__(self, attacker_id: int, action_type: str, part_type: Optional[str], target_id: Optional[int], target_part: Optional[str] = None):
        self.attacker_id = attacker_id
        self.action_type = action_type # "attack", "skip" など
        self.part_type = part_type     # "head", "right_arm", "left_arm"
        
        # ターゲット情報
        self.original_target_id = target_id
        self.current_target_id = target_id # 「かばう」等で変更される可能性がある現在のターゲット
        
        self.desired_target_part = target_part # 攻撃側が狙った部位
        
        # 計算結果 (InitiationSystemで事前に計算して格納する)
        self.calculation_result: Optional[Dict[str, Any]] = None
        
        # 状態
        self.status = "created"
        self.executed = False