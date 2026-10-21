"""コマンドメニューの項目情報（CommandMenuItemModel）を組み立てるビルダーロジック。"""
from typing import List, Mapping, Optional, Sequence, Tuple, TYPE_CHECKING

from domain.constants import ACTIONABLE_PART_TYPES, CommandSlot, PartType
from domain.action_logic import get_action_definition
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

    for part_type in ACTIONABLE_PART_TYPES:
        slot = CommandSlot.from_key(part_type.value)
        part = actor.get_part(part_type) if actor else None

        if part is None or slot is None:
            items.append(CommandMenuItemModel(
                slot_type=slot or CommandSlot.SKIP,
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
            slot_type=slot,
            label=part.name,
            action_label=get_action_definition(part.action).name,
            visual_enabled=visual_enabled,
            selectable=selectable,
            preview_target_robot_index=preview_index,
        ))

    items.append(CommandMenuItemModel(
        slot_type=CommandSlot.SKIP,
        label=SKIP_LABEL,
        action_label=SKIP_ACTION_LABEL,
        visual_enabled=True,
        selectable=True,
    ))

    return items


def to_selectable_mask(items: Sequence[CommandMenuItemModel]) -> List[bool]:
    """項目一覧から選択可能フラグのリストを抽出する"""
    return [item.selectable for item in items]


def _resolve_robot_index(
    target_info: Optional[Tuple['Robot', Optional[PartType]]],
    robots: Sequence['Robot'],
) -> Optional[int]:
    if not target_info:
        return None
    return find_robot_index(robots, target_info[0])