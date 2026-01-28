"""行動コマンドを表す一時的なコンポーネント"""

from dataclasses import dataclass
from typing import Optional
from core.ecs import Component

@dataclass
class ActionCommandComponent(Component):
    """
    プレイヤーまたはAIの「決定」を保持する。
    CommandSystemによってチャージ開始処理が行われたあと削除される。
    """
    action_type: str            # "attack", "skip"
    part_type: Optional[str] = None # "head", "right_arm", "left_arm"