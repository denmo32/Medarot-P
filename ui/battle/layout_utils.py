"""UIレイアウト計算用ユーティリティ（純粋関数）"""

import pygame
from ui.config import UI_PARAMS, SCREEN_WIDTH

def calculate_action_menu_layout(button_count: int) -> list[pygame.Rect]:
    """
    アクションメニューのボタン配置を計算し、Rectのリストを返す。
    InputSystem（判定）とBattleUIRenderer（描画）で共有される。
    
    配置ルール:
    - Index 0 (Head): 上段中央
    - Index 1 (Right): 下段左
    - Index 2 (Left): 下段右
    - Index 3+ (Skip等): 右側に配置
    """
    wy = UI_PARAMS['MESSAGE_WINDOW_Y']
    # wh = UI_PARAMS['MESSAGE_WINDOW_HEIGHT']
    
    ui_cfg = UI_PARAMS['UI']
    btn_w = ui_cfg['BTN_WIDTH']
    btn_h = ui_cfg['BTN_HEIGHT']
    btn_pad = ui_cfg['BTN_PADDING']
    
    layout = []
    center_x = SCREEN_WIDTH // 2
    
    # 基準となるY座標（ウィンドウ上部から少し下げた位置）
    start_y = wy + 25
    
    for i in range(button_count):
        rect = pygame.Rect(0, 0, btn_w, btn_h)
        
        if i == 0:
            # 頭部：上段中央
            rect.centerx = center_x
            rect.top = start_y
        elif i == 1:
            # 右腕：下段左（画面上では左側）
            rect.right = center_x - (btn_pad // 2)
            rect.top = start_y + btn_h + btn_pad
        elif i == 2:
            # 左腕：下段右（画面上では右側）
            rect.left = center_x + (btn_pad // 2)
            rect.top = start_y + btn_h + btn_pad
        else:
            # その他（スキップなど）：右端へ
            # 下段右のさらに右側に配置
            rect.left = center_x + btn_w + btn_pad * 2
            rect.centery = start_y + btn_h + (btn_pad // 2)

        layout.append(rect)
        
    return layout