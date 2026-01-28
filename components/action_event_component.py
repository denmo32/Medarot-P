"""行動イベントを表すコンポーネント"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from core.ecs import Component

if TYPE_CHECKING:
    from battle.mechanics.combat import CombatResult

@dataclass
class ActionEventComponent(Component):
    """
    1回の行動（攻撃など）の情報を保持する。
    InitiationSystemで生成され、ResolutionSystemで解決・削除される。
    """
    attacker_id: int
    action_type: str            # "attack", "skip" など
    part_type: Optional[str]
    target_id: Optional[int]
    target_part: Optional[str] = None

    # 以下は内部管理用フィールド（初期化時は自動設定）
    original_target_id: Optional[int] = field(init=False)
    current_target_id: Optional[int] = field(init=False)
    desired_target_part: Optional[str] = field(init=False)
    
    # 計算結果
    calculation_result: Optional['CombatResult'] = field(init=False, default=None)
    
    status: str = field(init=False, default="created")
    executed: bool = field(init=False, default=False)

    def __post_init__(self):
        self.original_target_id = self.target_id
        self.current_target_id = self.target_id
        self.desired_target_part = self.target_part