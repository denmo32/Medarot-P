"""カスタマイズ画面専用のレンダラー"""

import pygame
from config import COLORS, GAME_PARAMS
# インポート先を変更
from ui.base.renderer import BaseRenderer

class CustomizeRenderer(BaseRenderer):
    """カスタマイズ画面の3カラムレイアウトを描画"""

    def __init__(self, screen):
        super().__init__(screen)
        cfg = GAME_PARAMS['CUSTOMIZE']
        self.padding = cfg['PANEL_PADDING']
        self.y = cfg['PANEL_Y']
        self.height = cfg['PANEL_HEIGHT']
        
        self.cols = [
            {'x': self.padding, 'w': cfg['COLUMN_1_WIDTH'], 'title': "機体選択"},
            {'x': self.padding * 2 + cfg['COLUMN_1_WIDTH'], 'w': cfg['COLUMN_2_WIDTH'], 'title': ""},
            {'x': self.padding * 3 + cfg['COLUMN_1_WIDTH'] + cfg['COLUMN_2_WIDTH'], 'w': cfg['COLUMN_3_WIDTH'], 'title': ""}
        ]

    def render(self, ui_data):
        self.clear()
        self._draw_column_1(ui_data)
        self._draw_column_2(ui_data)
        self._draw_column_3(ui_data)

    def _draw_panel_base(self, col_idx, title):
        col = self.cols[col_idx]
        rect = (col['x'], self.y, col['w'], self.height)
        self.draw_box(rect, COLORS['PANEL_BG'], COLORS['PANEL_BORDER'])
        self.draw_text(title, (col['x'] + 10, self.y + 10), (150, 160, 180), 'normal')
        pygame.draw.line(self.screen, COLORS['PANEL_BORDER'], (col['x'] + 10, self.y + 35), (col['x'] + col['w'] - 10, self.y + 35))

    def _draw_column_1(self, data):
        self._draw_panel_base(0, "機体選択")
        col = self.cols[0]
        for i in range(3):
            bx, by, bw, bh = col['x'] + 10, self.y + 50 + i * 50, col['w'] - 20, 40
            if data['machine_idx'] == i and data['state'] == "machine_select":
                pygame.draw.rect(self.screen, COLORS['SELECT_HIGHLIGHT'], (bx, by, bw, bh))
            self.draw_text(f"機体{i+1}", (bx + 15, by + 8), COLORS['TEXT'], 'medium')

    def _draw_column_2(self, data):
        self._draw_panel_base(1, data['machine_name'])
        col = self.cols[1]
        
        # 解決済みのスロット情報を表示
        for i, slot in enumerate(data['slots_info']):
            bx, by, bw, bh = col['x'] + 10, self.y + 50 + i * 45, col['w'] - 20, 35
            if data['slot_idx'] == i and data['state'] != "machine_select":
                pygame.draw.rect(self.screen, COLORS['SELECT_HIGHLIGHT'], (bx, by, bw, bh))
            self.draw_text(slot['label'], (bx + 10, by + 7), (180, 190, 200))
            self.draw_text(slot['part_name'], (bx + 80, by + 7))

        list_y = self.y + 280
        pygame.draw.line(self.screen, COLORS['PANEL_BORDER'], (col['x'] + 10, list_y), (col['x'] + col['w'] - 10, list_y))
        self.draw_text(f"パーツ一覧", (col['x'] + 10, list_y + 10), (150, 160, 180))

        # 解決済みのリストアイテムを表示
        for i, item in enumerate(data['available_list']):
            by = list_y + 40 + i * 35
            if by > self.y + self.height - 30: break
            if data['state'] == "part_list_select" and data['part_list_idx'] == i:
                pygame.draw.rect(self.screen, (60, 80, 100), (col['x'] + 10, by - 2, col['w'] - 30, 28))
                pygame.draw.rect(self.screen, COLORS['SELECT_HIGHLIGHT'], (col['x'] + 10, by - 2, 5, 28))
            color = COLORS['TEXT'] if (data['state'] == "part_list_select" and data['part_list_idx'] == i) else (180, 180, 180)
            self.draw_text(item['name'], (col['x'] + 25, by), color)

    def _draw_column_3(self, data):
        title = "メダル詳細" if data['slot_idx'] == 0 else "パーツ詳細"
        self._draw_panel_base(2, title)
        col, fd = self.cols[2], data['focused_data']
        if not fd: return
        self.draw_text(fd.get('name', '---'), (col['x'] + 15, self.y + 50), COLORS['SELECT_HIGHLIGHT'], 'medium')
        
        attr_label = data['focused_attr_label']
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
        
        for i, (label, val) in enumerate(stats):
            by = self.y + 100 + i * 40
            pygame.draw.line(self.screen, (50, 60, 75), (col['x'] + 15, by + 30), (col['x'] + col['w'] - 15, by + 30))
            self.draw_text(label, (col['x'] + 15, by + 5), (150, 160, 180))
            self.draw_text(str(val), (col['x'] + col['w'] - 20, by + 5), COLORS['TEXT'], 'medium', 'right')