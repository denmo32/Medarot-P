# features/battle/presentation/command_menu_builder.py
"""コマンドメニューの項目情報（CommandMenuItemModel）を組み立てるビルダーロジック。"""
from typing import List, Mapping, Optional, Sequence, Tuple, TYPE_CHECKING

from domain.constants import COMMAND_MENU_PART_ORDER, PartType
from features.battle.context import find_robot_index
from .view_models import CommandMenuItemModel

if TYPE_CHECKING:
    from features.battle.entities.robot import Robot

SKIP_LABEL = "スキップ"
SKIP_ACTION_LABEL = "なし"
EMPTY_LABEL = "---"


def build_command_menu_items(
    actor: Optional['Robot'],
    preview_targets: Mapping[PartType, Optional[Tuple['Robot', Optional[PartType]]]],
    robots: Sequence['Robot'],
) -> List[CommandMenuItemModel]:
    """現在のアクター機体とターゲット情報からメニュー項目モデルの一覧を生成する"""
    items: List[CommandMenuItemModel] = []

    for part_type in COMMAND_MENU_PART_ORDER:
        if part_type is None:
            # スキップ項目
            items.append(CommandMenuItemModel(
                part_type=None,
                label=SKIP_LABEL,
                action_label=SKIP_ACTION_LABEL,
                visual_enabled=True,
                selectable=True,
            ))
            continue

        part = actor.get_part(part_type) if actor else None

        if part is None:
            items.append(CommandMenuItemModel(
                part_type=part_type,
                label=EMPTY_LABEL,
                action_label="",
                visual_enabled=False,
                selectable=False,
            ))
            continue

        visual_enabled = part.can_execute
        preview_index = _resolve_robot_index(preview_targets.get(part_type), robots)

        selectable = visual_enabled
        if selectable and part.locks_target and preview_index is None:
            selectable = False

        items.append(CommandMenuItemModel(
            part_type=part_type,
            label=part.name,
            action_label=part.action.value if part.action else "",
            visual_enabled=visual_enabled,
            selectable=selectable,
            preview_target_robot_index=preview_index,
        ))

    return items


def _resolve_robot_index(
    target_info: Optional[Tuple['Robot', Optional[PartType]]],
    robots: Sequence['Robot'],
) -> Optional[int]:
    if not target_info:
        return None
    return find_robot_index(robots, target_info[0])