"""メニュー操作（マウス）の共通ロジック。"""
from typing import List, Tuple

import pygame


def handle_menu_mouse(
    mouse_pos: Tuple[int, int],
    mouse_clicked: bool,
    layouts: List[pygame.Rect],
    current_idx: int,
) -> Tuple[int, bool]:
    """マウスによる選択・決定ロジック。

    戻り値:
        (new_index, confirmed)
        new_index: 更新後の選択インデックス
        confirmed: 決定（実行）された場合は True
    """
    hit_idx = None
    for i, rect in enumerate(layouts):
        if rect.collidepoint(mouse_pos):
            hit_idx = i
            break

    if mouse_clicked and hit_idx is not None:
        if current_idx == hit_idx:
            return hit_idx, True
        return hit_idx, False

    return current_idx, False
