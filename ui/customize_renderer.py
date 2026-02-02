"""カスタマイズ画面専用のレンダラー"""

import pygame
from ui.config import COLORS, UI_PARAMS
from ui.base.renderer import BaseRenderer

class CustomizeRenderer(BaseRenderer):
    """カスタマイズ画面の3カラムレイアウトを描画（相対座標対応）"""

    def __init__(self, screen):
        super().__init__(screen)

    def _calc_layout(self):
        sw, sh = self.get_screen_size()
        cfg = UI_PARAMS['CUSTOMIZE']
        
        self.padding = int(sw * cfg['PANEL_PADDING_RATIO'])
        self.y = int(sh * cfg['PANEL_Y_RATIO'])
        self.height = int(sh * cfg['PANEL_HEIGHT_RATIO'])
        
        col1_w = int(sw * cfg['COLUMN_1_WIDTH_RATIO'])
        col2_w = int(sw * cfg['COLUMN_2_WIDTH_RATIO'])
        col3_w = int(sw * cfg['COLUMN_3_WIDTH_RATIO'])
        
        self.cols = [
            {'x': self.padding, 'w': col1_w, 'title': "機体選択"},
            {'x': self.padding * 2 + col1_w, 'w': col2_w, 'title': ""},
            {'x': self.padding * 3 + col1_w + col2_w, 'w': col3_w, 'title': ""}
        ]

    def render(self, ui_data):
        self.clear()
        self._calc_layout() # 毎フレーム計算してリサイズに対応
        self._draw_column_1(ui_data)
        self._draw_column_2(ui_data)
        self._draw_column_3(ui_data)

    def _draw_panel_base(self, col_idx, title):
        col = self.cols[col_idx]
        rect = (col['x'], self.y, col['w'], self.height)
        self.draw_box(rect, COLORS['PANEL_BG'], COLORS['PANEL_BORDER'])
        self.draw_text(title, (col['x'] + 10, self.y + 10), (150, 160, 180), 'normal')
        line_y = self.y + self.scale_y(0.06)
        pygame.draw.line(self.screen, COLORS['PANEL_BORDER'], (col['x'] + 10, line_y), (col['x'] + col['w'] - 10, line_y))
        return line_y # コンテンツ開始Y座標として返す

    def _draw_column_1(self, data):
        start_y = self._draw_panel_base(0, "機体選択")
        col = self.cols[0]
        item_h = self.scale_y(0.07)
        gap = self.scale_y(0.02)

        for i in range(3):
            bx, by = col['x'] + 10, start_y + gap + i * (item_h + gap)
            bw, bh = col['w'] - 20, item_h
            if data['machine_idx'] == i and data['state'] == "machine_select":
                pygame.draw.rect(self.screen, COLORS['SELECT_HIGHLIGHT'], (bx, by, bw, bh))
            self.draw_text(f"機体{i+1}", (bx + 15, by + bh//4), COLORS['TEXT'], 'medium')

    def _draw_column_2(self, data):
        start_y = self._draw_panel_base(1, data['machine_name'])
        col = self.cols[1]
        item_h = self.scale_y(0.06)
        gap = self.scale_y(0.015)
        
        # スロット情報
        for i, slot in enumerate(data['slots_info']):
            bx, by = col['x'] + 10, start_y + gap + i * (item_h + gap)
            bw, bh = col['w'] - 20, item_h
            if data['slot_idx'] == i and data['state'] != "machine_select":
                pygame.draw.rect(self.screen, COLORS['SELECT_HIGHLIGHT'], (bx, by, bw, bh))
            self.draw_text(slot['label'], (bx + 10, by + bh//4), (180, 190, 200))
            self.draw_text(slot['part_name'], (bx + 80, by + bh//4))

        # リスト区切り
        list_start_y = start_y + gap + len(data['slots_info']) * (item_h + gap) + gap * 2
        pygame.draw.line(self.screen, COLORS['PANEL_BORDER'], (col['x'] + 10, list_start_y), (col['x'] + col['w'] - 10, list_start_y))
        self.draw_text(f"パーツ一覧", (col['x'] + 10, list_start_y + 10), (150, 160, 180))

        # リストアイテム
        list_item_start_y = list_start_y + 40
        list_item_h = self.scale_y(0.05)
        
        for i, item in enumerate(data['available_list']):
            by = list_item_start_y + i * list_item_h
            if by > self.y + self.height - list_item_h: break
            
            if data['state'] == "part_list_select" and data['part_list_idx'] == i:
                pygame.draw.rect(self.screen, (60, 80, 100), (col['x'] + 10, by, col['w'] - 30, list_item_h - 2))
                pygame.draw.rect(self.screen, COLORS['SELECT_HIGHLIGHT'], (col['x'] + 10, by, 5, list_item_h - 2))
            
            color = COLORS['TEXT'] if (data['state'] == "part_list_select" and data['part_list_idx'] == i) else (180, 180, 180)
            self.draw_text(item['name'], (col['x'] + 25, by + 2), color)

    def _draw_column_3(self, data):
        title = "メダル詳細" if data['slot_idx'] == 0 else "パーツ詳細"
        start_y = self._draw_panel_base(2, title)
        col, fd = self.cols[2], data['focused_data']
        if not fd: return
        
        gap = self.scale_y(0.03)
        self.draw_text(fd.get('name', '---'), (col['x'] + 15, start_y + gap), COLORS['SELECT_HIGHLIGHT'], 'medium')
        
        attr_label = data['focused_attr_label']
        stats = []
        if data['slot_idx'] == 0:
            stats = [("ニックネーム", fd.get('nickname', '---')), 
                     ("性格", fd.get('personality', 'random')),
                     ("属性", attr_label)]
        else:
            stats = [("属性", attr_label),
                     ("装甲", fd.get('hp', 0)), 
                     ("威力", fd.get('attack', '---')), 
                     ("機動", fd.get('mobility', '---')), 
                     ("耐久", fd.get('defense', '---'))]
        
        info_start_y = start_y + gap + 40
        row_h = self.scale_y(0.07)
        
        for i, (label, val) in enumerate(stats):
            by = info_start_y + i * row_h
            line_y = by + row_h - 5
            pygame.draw.line(self.screen, (50, 60, 75), (col['x'] + 15, line_y), (col['x'] + col['w'] - 15, line_y))
            self.draw_text(label, (col['x'] + 15, by + 5), (150, 160, 180))
            self.draw_text(str(val), (col['x'] + col['w'] - 20, by + 5), COLORS['TEXT'], 'medium', 'right')