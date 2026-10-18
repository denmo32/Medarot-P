"""タイトル画面のレイアウト・当たり判定計算（ステートレス純粋関数）。"""
from typing import Sequence, Tuple
import pygame

from features.title.view_models import TitleButtonModel
from ui.base.interaction import handle_menu_mouse


def calculate_button_layouts(
    screen_size: Tuple[int, int], buttons: Sequence[TitleButtonModel]
) -> list[pygame.Rect]:
    """ボタン定義に基づいて、画面サイズに合わせた Rect のリストを計算する。"""
    sw, sh = screen_size
    layouts = []
    for btn in buttons:
        w, h = sw * btn.w_ratio, sh * btn.h_ratio
        x = sw * btn.cx - w / 2
        y = sh * btn.cy - h / 2
        layouts.append(pygame.Rect(x, y, w, h))
    return layouts


def hit_test_title_buttons(
    screen_size: Tuple[int, int],
    mouse_pos: Tuple[int, int],
    buttons: Sequence[TitleButtonModel],
    current_index: int,
) -> Tuple[int, bool]:
    """タイトルボタンに対する純粋な当たり判定を行い、(新インデックス, 決定フラグ) を返す。"""
    layouts = calculate_button_layouts(screen_size, buttons)
    return handle_menu_mouse(mouse_pos, True, layouts, current_index)
