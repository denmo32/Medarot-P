"""UIレイアウト計算用ユーティリティ（純粋関数）"""

import pygame
from ui.config import UI_PARAMS

def calculate_action_menu_layout(button_count: int, screen_size: tuple[int, int]) -> list[pygame.Rect]:
    """
    アクションメニューのボタン配置を計算し、Rectのリストを返す。
    画面サイズに基づいて動的に計算する。
    """
    sw, sh = screen_size
    
    # パラメータ（比率）
    wy_ratio = UI_PARAMS['MESSAGE_WINDOW_Y_RATIO']
    btn_w_ratio = UI_PARAMS['UI']['BTN_WIDTH_RATIO']
    btn_h_ratio = UI_PARAMS['UI']['BTN_HEIGHT_RATIO']
    pad_ratio = UI_PARAMS['UI']['BTN_PADDING_RATIO']
    
    btn_w = int(sw * btn_w_ratio)
    btn_h = int(sh * btn_h_ratio)
    btn_pad = int(sw * pad_ratio)
    
    start_y = int(sh * wy_ratio) + int(sh * 0.04) # ウィンドウ上部から少し下げる
    center_x = sw // 2
    
    layout = []
    
    for i in range(button_count):
        rect = pygame.Rect(0, 0, btn_w, btn_h)
        
        if i == 0:
            # 頭部：上段中央
            rect.centerx = center_x
            rect.top = start_y
        elif i == 1:
            # 右腕：下段左
            rect.right = center_x - (btn_pad // 2)
            rect.top = start_y + btn_h + btn_pad
        elif i == 2:
            # 左腕：下段右
            rect.left = center_x + (btn_pad // 2)
            rect.top = start_y + btn_h + btn_pad
        else:
            # スキップ等：右端へ
            rect.left = center_x + btn_w + btn_pad * 2
            rect.centery = start_y + btn_h + (btn_pad // 2)

        layout.append(rect)
        
    return layout