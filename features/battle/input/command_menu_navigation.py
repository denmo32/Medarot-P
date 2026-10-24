"""コマンドメニューの十字キー移動規則。"""
from typing import Dict, Sequence
from core.inputs import InputState
from domain.constants import (
    COMMAND_MENU_HEAD_INDEX,
    COMMAND_MENU_RIGHT_ARM_INDEX,
    COMMAND_MENU_LEFT_ARM_INDEX,
    COMMAND_MENU_MEDAFORCE_INDEX,
)

# 完全対称な十字配置のトポロジー
COMMAND_MENU_TRANSITIONS: Dict[int, Dict[str, int]] = {
    COMMAND_MENU_HEAD_INDEX: {
        "down": COMMAND_MENU_MEDAFORCE_INDEX,
        "left": COMMAND_MENU_RIGHT_ARM_INDEX,
        "right": COMMAND_MENU_LEFT_ARM_INDEX,
    },
    COMMAND_MENU_RIGHT_ARM_INDEX: {
        "up": COMMAND_MENU_HEAD_INDEX,
        "down": COMMAND_MENU_MEDAFORCE_INDEX,
        "right": COMMAND_MENU_LEFT_ARM_INDEX,
    },
    COMMAND_MENU_LEFT_ARM_INDEX: {
        "up": COMMAND_MENU_HEAD_INDEX,
        "down": COMMAND_MENU_MEDAFORCE_INDEX,
        "left": COMMAND_MENU_RIGHT_ARM_INDEX,
    },
    COMMAND_MENU_MEDAFORCE_INDEX: {
        "up": COMMAND_MENU_HEAD_INDEX,
        "left": COMMAND_MENU_RIGHT_ARM_INDEX,
        "right": COMMAND_MENU_LEFT_ARM_INDEX,
    },
}


def resolve_command_menu_navigation(
    current_index: int,
    input_state: InputState,
    selectable_mask: Sequence[bool],
) -> int:
    direction = None
    if input_state.btn_up:
        direction = "up"
    elif input_state.btn_down:
        direction = "down"
    elif input_state.btn_left:
        direction = "left"
    elif input_state.btn_right:
        direction = "right"

    if direction is None:
        return current_index

    target_map = COMMAND_MENU_TRANSITIONS.get(current_index, {})
    new_index = target_map.get(direction, current_index)

    if 0 <= new_index < len(selectable_mask) and selectable_mask[new_index]:
        return new_index

    return current_index