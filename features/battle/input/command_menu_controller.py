"""コマンドメニューのカーソル状態と入力解決を担当するコントローラ。

※ 本モジュールは Input/Presentation 境界に位置し、マウスクリック解決のために
   ui.layout のヒットテスト関数を参照することを許容します。
"""
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from core.inputs import InputState
from domain.constants import PartType
from features.battle.input.command_menu_navigation import resolve_command_menu_navigation
from features.battle.presentation.view_models import CommandMenuItemModel
from features.battle.ui.layout import hit_test_command_menu


@dataclass(frozen=True)
class MenuInputResult:
    """コマンドメニューの入力解決結果"""
    cursor_index: int
    confirmed: bool = False
    chosen_part: Optional[PartType] = None


class CommandMenuController:
    """コマンドメニューのカーソル移動・マウスクリック解決を一元管理する"""

    def __init__(self):
        self.selected_index: int = 0

    def reset(self):
        """カーソル位置を初期位置（頭部: 0）に戻す"""
        self.selected_index = 0

    def resolve_input(
        self,
        input_state: InputState,
        menu_items: Sequence[CommandMenuItemModel],
        screen_size: Optional[Tuple[int, int]] = None,
    ) -> MenuInputResult:
        """入力を処理し、MenuInputResult を返す。"""
        selectable_mask = tuple(item.selectable for item in menu_items)
        if not selectable_mask:
            return MenuInputResult(cursor_index=self.selected_index, confirmed=False)

        # 1. マウスクリックの判定（解像度情報がある場合）
        if input_state.mouse_clicked and screen_size is not None:
            new_idx, confirmed = hit_test_command_menu(
                screen_size,
                (input_state.mouse_x, input_state.mouse_y),
                len(menu_items),
                self.selected_index,
            )
            if 0 <= new_idx < len(selectable_mask) and selectable_mask[new_idx]:
                self.selected_index = new_idx
                if confirmed:
                    return MenuInputResult(
                        cursor_index=self.selected_index,
                        confirmed=True,
                        chosen_part=menu_items[new_idx].part_type,
                    )

        # 2. 十字キーによるカーソル遷移
        self.selected_index = resolve_command_menu_navigation(
            self.selected_index, input_state, selectable_mask
        )

        # 3. 決定キーによる確定（選択可能項目であることのガード付き）
        if input_state.btn_ok and selectable_mask[self.selected_index]:
            return MenuInputResult(
                cursor_index=self.selected_index,
                confirmed=True,
                chosen_part=menu_items[self.selected_index].part_type,
            )

        return MenuInputResult(cursor_index=self.selected_index, confirmed=False)