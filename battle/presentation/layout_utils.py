"""UIレイアウト計算用ユーティリティ（純粋関数）"""

import pygame
from config import GAME_PARAMS

def calculate_action_menu_layout(button_count: int) -> list[pygame.Rect]:
    """
    アクションメニューのボタン配置を計算し、Rectのリストを返す。
    InputSystem（判定）とBattleUIRenderer（描画）で共有される。
    """
    wx = 0
    wy = GAME_PARAMS['MESSAGE_WINDOW_Y']
    wh = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
    pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']
    ui_cfg = GAME_PARAMS['UI']

    btn_y = wy + wh - ui_cfg['BTN_Y_OFFSET']
    btn_w = ui_cfg['BTN_WIDTH']
    btn_h = ui_cfg['BTN_HEIGHT']
    btn_pad = ui_cfg['BTN_PADDING']
    
    layout = []
    for i in range(button_count):
        bx = wx + pad + i * (btn_w + btn_pad)
        layout.append(pygame.Rect(bx, btn_y, btn_w, btn_h))
        
    return layout