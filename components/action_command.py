"""行動コマンドを表す一時的なコンポーネント"""

from typing import Optional
from core.ecs import Component

class ActionCommandComponent(Component):
    """
    プレイヤーまたはAIの「決定」を保持する。
    CommandSystemによってチャージ開始処理が行われたあと削除される。
    """
    def __init__(self, action_type: str, part_type: Optional[str] = None):
        self.action_type = action_type # "attack", "skip"
        self.part_type = part_type     # "head", "right_arm", "left_arm"