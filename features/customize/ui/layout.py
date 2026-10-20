"""カスタマイズ画面の座標・矩形計算。"""
from typing import List, Optional, Tuple
import pygame

from domain.config import PLAYER_COUNT
from domain.constants import CustomizeState
from ui_base.interaction import handle_menu_mouse
from ui_base.config import SCREEN_HEIGHT
from features.customize.ui.config import CUSTOMIZE_UI_PARAMS
from features.customize.presentation.view_models import CustomizeViewModel


def _ui_scale(screen_size: Tuple[int, int]) -> float:
    return screen_size[1] / SCREEN_HEIGHT


def _scaled(value: float, screen_size: Tuple[int, int]) -> int:
    return int(value * _ui_scale(screen_size))


def get_state_rects(layout: dict, state: CustomizeState) -> List[pygame.Rect]:
    state_enum = CustomizeState.from_key(state)
    if state_enum == CustomizeState.ROBOT_SELECT:
        return layout.get('robot_rects', [])
    if state_enum == CustomizeState.SLOT_SELECT:
        return layout.get('slot_rects', [])
    if state_enum == CustomizeState.PART_LIST_SELECT:
        return layout.get('part_list_rects', [])
    return []


def calculate_customize_layout(
    screen_size: Tuple[int, int],
    model: Optional[CustomizeViewModel] = None,
) -> dict:
    sw, sh = screen_size
    cfg = CUSTOMIZE_UI_PARAMS

    padding = int(sw * cfg['PANEL_PADDING_RATIO'])
    y = int(sh * cfg['PANEL_Y_RATIO'])
    height = int(sh * cfg['PANEL_HEIGHT_RATIO'])

    col1_w = int(sw * cfg['COLUMN_1_WIDTH_RATIO'])
    col2_w = int(sw * cfg['COLUMN_2_WIDTH_RATIO'])
    col3_w = int(sw * cfg['COLUMN_3_WIDTH_RATIO'])

    cols = [
        {'x': padding, 'w': col1_w, 'title': "機体選択"},
        {'x': padding * 2 + col1_w, 'w': col2_w, 'title': ""},
        {'x': padding * 3 + col1_w + col2_w, 'w': col3_w, 'title': ""},
    ]

    content_start_y = y + int(sh * cfg['CONTENT_START_Y_RATIO'])

    c1_item_h = int(sh * cfg['COLUMN_1_ITEM_HEIGHT_RATIO'])
    c1_gap = int(sh * cfg['COLUMN_1_ITEM_GAP_RATIO'])
    c1_pad = _scaled(cfg['COLUMN_1_ITEM_PADDING'], screen_size)
    robot_rects = [
        pygame.Rect(
            cols[0]['x'] + c1_pad,
            content_start_y + c1_gap + i * (c1_item_h + c1_gap),
            cols[0]['w'] - c1_pad * 2,
            c1_item_h,
        )
        for i in range(PLAYER_COUNT)
    ]

    c2_item_h = int(sh * cfg['COLUMN_2_ITEM_HEIGHT_RATIO'])
    c2_gap = int(sh * cfg['COLUMN_2_ITEM_GAP_RATIO'])
    c2_text_pad = _scaled(cfg['COLUMN_2_TEXT_OFFSET_X'], screen_size)

    if isinstance(model, CustomizeViewModel):
        slots_count = model.slot_count
        available_count = model.part_list_count
    else:
        slots_count = 5
        available_count = 0

    slot_rects = [
        pygame.Rect(
            cols[1]['x'] + c2_text_pad,
            content_start_y + c2_gap + i * (c2_item_h + c2_gap),
            cols[1]['w'] - c2_text_pad * 2,
            c2_item_h,
        )
        for i in range(slots_count)
    ]

    list_start_y = content_start_y + c2_gap + slots_count * (c2_item_h + c2_gap) + c2_gap * 2
    list_item_start_y = list_start_y + _scaled(cfg['COLUMN_2_LIST_START_PADDING'], screen_size)
    list_item_h = int(sh * cfg['COLUMN_2_LIST_ITEM_HEIGHT_RATIO'])
    list_indent = _scaled(cfg['COLUMN_2_LIST_INDENT'], screen_size)

    part_list_rects = []
    for i in range(available_count):
        by = list_item_start_y + i * list_item_h
        if by > y + height - list_item_h:
            break
        part_list_rects.append(
            pygame.Rect(
                cols[1]['x'] + c2_text_pad,
                by,
                cols[1]['w'] - list_indent,
                list_item_h - _scaled(2, screen_size),
            )
        )

    return {
        'padding': padding,
        'y': y,
        'height': height,
        'cols': cols,
        'content_start_y': content_start_y,
        'robot_rects': robot_rects,
        'slot_rects': slot_rects,
        'list_start_y': list_start_y,
        'part_list_rects': part_list_rects,
    }


def hit_test_customize(
    screen_size: Tuple[int, int],
    mouse_pos: Tuple[int, int],
    state: CustomizeState,
    current_idx: int,
    model: Optional[CustomizeViewModel] = None,
) -> Tuple[int, bool]:
    """カスタマイズ画面に対する純粋な幾何当たり判定を行う"""
    layout = calculate_customize_layout(screen_size, model)
    rects = get_state_rects(layout, state)
    if not rects:
        return current_idx, False
    return handle_menu_mouse(mouse_pos, True, rects, current_idx)