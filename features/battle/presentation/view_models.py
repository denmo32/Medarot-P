"""バトル画面の表示専用データ構造（UIへの逆依存を排除した純粋DTO）。"""
from dataclasses import dataclass
from typing import Optional

from domain.constants import PartType


@dataclass(frozen=True)
class CommandMenuItemModel:
    """コマンドメニュー項目の表示用モデル（part_type=None はスキップを表す）"""
    part_type: Optional[PartType]
    label: str
    action_label: str
    visual_enabled: bool
    selectable: bool
    preview_target_robot_index: Optional[int] = None