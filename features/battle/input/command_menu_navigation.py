"""コマンドメニューの十字キー移動規則。

レイアウト計算（ui/battle/layout.py）とは独立した、バトルメニュー固有の
入力規則のみを扱う。pygame には依存しない。
"""
from typing import Dict, Sequence

from core.inputs import InputState
from domain.constants import (
    COMMAND_MENU_HEAD_INDEX,
    COMMAND_MENU_LEFT_ARM_INDEX,
    COMMAND_MENU_RIGHT_ARM_INDEX,
    COMMAND_MENU_SKIP_INDEX,
)

# ダイアモンド配置のトポロジー（現在インデックス -> {入力方向: 遷移先インデックス}）
COMMAND_MENU_TRANSITIONS: Dict[int, Dict[str, int]] = {
    COMMAND_MENU_HEAD_INDEX: {
        "down": COMMAND_MENU_SKIP_INDEX,
        "left": COMMAND_MENU_RIGHT_ARM_INDEX,
        "right": COMMAND_MENU_LEFT_ARM_INDEX,
    },
    COMMAND_MENU_RIGHT_ARM_INDEX: {
        "up": COMMAND_MENU_HEAD_INDEX,
        "right": COMMAND_MENU_LEFT_ARM_INDEX,
        "down": COMMAND_MENU_SKIP_INDEX,
    },
    COMMAND_MENU_LEFT_ARM_INDEX: {
        "up": COMMAND_MENU_HEAD_INDEX,
        "left": COMMAND_MENU_RIGHT_ARM_INDEX,
        "down": COMMAND_MENU_SKIP_INDEX,
    },
    COMMAND_MENU_SKIP_INDEX: {
        "up": COMMAND_MENU_HEAD_INDEX,
        "left": COMMAND_MENU_LEFT_ARM_INDEX,
        "right": COMMAND_MENU_LEFT_ARM_INDEX,
    },
}


def resolve_command_menu_navigation(
    current_index: int,
    input_state: InputState,
    selectable_mask: Sequence[bool],
) -> int:
    """入力に基づく次の選択インデックスを計算して返す（純粋関数）。

    移動先が選択不可（selectable が False）の場合は現在位置を維持する。
    """
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