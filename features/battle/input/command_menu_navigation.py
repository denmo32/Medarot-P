"""コマンドメニューの十字キー移動規則。

レイアウト計算（ui/battle/layout.py）とは独立した、バトルメニュー固有の
入力規則のみを扱う。pygame には依存しない。
"""
from typing import Sequence


# Medarot-P の特殊な十字レイアウト
MENU_HEAD_INDEX = 0       # 頭部（上）
MENU_RIGHT_ARM_INDEX = 1  # 右腕（左下）
MENU_LEFT_ARM_INDEX = 2   # 左腕（右下）
MENU_SKIP_INDEX = 3       # スキップ（右）


def resolve_command_menu_navigation(
    current_index: int,
    input_state,
    selectable_mask: Sequence[bool],
) -> int:
    """入力に基づく次の選択インデックスを計算して返す（純粋関数）。

    `input_state` は btn_up/btn_down/btn_left/btn_right を持つ任意オブジェクト
    （core 側の InputState、ダックタイピング）を受け付ける。
    移動先が選択不可（selectable が False）の場合は現在位置を維持する。
    """
    new_index = current_index

    if input_state.btn_up:
        new_index = MENU_HEAD_INDEX
    elif input_state.btn_left:
        # スキップ(3)からは左腕(2)へ、それ以外は右腕(1)へ
        new_index = MENU_LEFT_ARM_INDEX if current_index == MENU_SKIP_INDEX else MENU_RIGHT_ARM_INDEX
    elif input_state.btn_right:
        # 右入力は常に左腕(2)を目指し、スキップ(3)へは遷移させない
        new_index = MENU_LEFT_ARM_INDEX
    elif input_state.btn_down:
        # 下入力でのみスキップ(3)へ移動する
        new_index = MENU_SKIP_INDEX

    if 0 <= new_index < len(selectable_mask) and selectable_mask[new_index]:
        return new_index

    return current_index
