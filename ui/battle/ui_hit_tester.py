"""
UI レイアウトと当たり判定を担当するユーティリティ。

ViewModel からレイアウト計算の責務を分離し、
Scene/Renderer 側で UI 座標の概念を完結させる。
"""

import pygame
from ui.config import UI_PARAMS, MENU_PART_ORDER


class UIHitTester:
    """
    UI 要素のレイアウト計算と当たり判定を担当する。

    このクラスは「画面ピクセル座標」の概念を持ち、
    ECS ロジック層（InputSystem など）とは完全に分離されている。
    """

    @staticmethod
    def calculate_action_menu_layout(button_count: int, screen_size: tuple[int, int]) -> list[pygame.Rect]:
        """
        アクションメニューのボタン配置を計算し、Rect のリストを返す。
        画面サイズに基づいて動的に計算する。
        
        このメソッドは ViewModel が Snapshot 生成時に呼び出すことを想定している。
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

        start_y = int(sh * wy_ratio) + int(sh * 0.04)  # ウィンドウ上部から少し下げる
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

    @staticmethod
    def hit_test_action_menu(mx: int, my: int, layouts: list[pygame.Rect]) -> int | None:
        """
        マウス座標がアクションメニューのどのボタンにあるかを判定。

        引数：
            mx, my: マウス座標
            layouts: pygame.Rect のリスト

        戻り値：
            ボタンのインデックス（0-based）。どのボタンにも該当しない場合は None。
        """
        for i, rect in enumerate(layouts):
            if rect.collidepoint(mx, my):
                return i
        return None

    @staticmethod
    def resolve_navigation(current_idx: int, btn_up: bool, btn_down: bool, btn_left: bool, btn_right: bool, max_idx: int) -> int:
        """
        キー入力に基づく次の選択インデックスを計算して返す（純粋関数）。
        
        Medarot-P の特殊な十字レイアウト：
        0: 頭部 (上)
        1: 右腕 (左下)
        2: 左腕 (右下)
        3: スキップ (右)
        """
        if btn_up:
            return 0
        if btn_left:
            return 1
        if btn_right:
            # 2 (左腕) の時は 3 (スキップ) へ、それ以外は 2 へ
            return 3 if current_idx == 2 else 2
        if btn_down:
            # 下入力時は「スキップ（3）」へ移動（利便性向上のための拡張）
            return 3
        return current_idx
