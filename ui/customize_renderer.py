"""カスタマイズ画面専用のレンダラー"""

import pygame
from config import COLORS, GAME_PARAMS, FONT_NAMES

class CustomizeRenderer:
    """カスタマイズ画面の3カラムレイアウトを描画"""

    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont(FONT_NAMES, 20)
        self.font_bold = pygame.font.SysFont(FONT_NAMES, 24)
        self.title_font = pygame.font.SysFont(FONT_NAMES, 28)
        
        cfg = GAME_PARAMS['CUSTOMIZE']
        self.padding = cfg['PANEL_PADDING']
        self.y = cfg['PANEL_Y']
        self.height = cfg['PANEL_HEIGHT']
        
        self.col1_x = self.padding
        self.col1_w = cfg['COLUMN_1_WIDTH']
        
        self.col2_x = self.col1_x + self.col1_w + self.padding
        self.col2_w = cfg['COLUMN_2_WIDTH']
        
        self.col3_x = self.col2_x + self.col2_w + self.padding
        self.col3_w = cfg['COLUMN_3_WIDTH']

    def render(self, ui_data):
        self.screen.fill(COLORS['BACKGROUND'])
        
        self._draw_column_1(ui_data)
        self._draw_column_2(ui_data)
        self._draw_column_3(ui_data)

    def _draw_panel(self, x, w, title):
        rect = pygame.Rect(x, self.y, w, self.height)
        pygame.draw.rect(self.screen, COLORS['PANEL_BG'], rect)
        pygame.draw.rect(self.screen, COLORS['PANEL_BORDER'], rect, 2)
        
        # タイトル
        t_surf = self.font.render(title, True, (150, 160, 180))
        self.screen.blit(t_surf, (x + 10, self.y + 10))
        pygame.draw.line(self.screen, COLORS['PANEL_BORDER'], (x + 10, self.y + 35), (x + w - 10, self.y + 35))

    def _draw_column_1(self, data):
        """機体選択"""
        self._draw_panel(self.col1_x, self.col1_w, "機体選択")
        
        names = ["サイカチス", "ロクショウ", "ドークス"]
        for i, name in enumerate(names):
            bx = self.col1_x + 10
            by = self.y + 50 + i * 50
            bw = self.col1_w - 20
            bh = 40
            
            is_selected = (data['machine_idx'] == i and data['state'] == "machine_select")
            if is_selected:
                pygame.draw.rect(self.screen, COLORS['SELECT_HIGHLIGHT'], (bx, by, bw, bh))
            
            color = COLORS['TEXT']
            txt = self.font_bold.render(name, True, color)
            self.screen.blit(txt, (bx + 15, by + 8))

    def _draw_column_2(self, data):
        """中央：パーツ構成 & パーツ一覧"""
        self._draw_panel(self.col2_x, self.col2_w, data['machine_name'])
        
        # 1. パーツ構成(スロット)
        slots = [("head", "頭部"), ("right_arm", "右腕"), ("left_arm", "左腕"), ("legs", "脚部")]
        pm = data['parts_setup']
        
        from data.parts_data_manager import get_parts_manager
        mgr = get_parts_manager()

        for i, (key, label) in enumerate(slots):
            bx = self.col2_x + 10
            by = self.y + 50 + i * 45
            bw = self.col2_w - 20
            bh = 35
            
            is_active = (data['slot_idx'] == i and data['state'] != "machine_select")
            if is_active:
                pygame.draw.rect(self.screen, COLORS['SELECT_HIGHLIGHT'], (bx, by, bw, bh))
            
            # 部位ラベル
            l_surf = self.font.render(label, True, (180, 190, 200))
            self.screen.blit(l_surf, (bx + 10, by + 7))
            
            # 装着パーツ名
            part_name = mgr.get_part_name(pm[key])
            n_surf = self.font.render(part_name, True, COLORS['TEXT'])
            self.screen.blit(n_surf, (bx + 100, by + 7))

        # 2. パーツ一覧(下半分)
        list_y = self.y + 250
        pygame.draw.line(self.screen, COLORS['PANEL_BORDER'], (self.col2_x + 10, list_y), (self.col2_x + self.col2_w - 10, list_y))
        
        t_label = slots[data['slot_idx']][1]
        t_surf = self.font.render(f"{t_label}一覧", True, (150, 160, 180))
        self.screen.blit(t_surf, (self.col2_x + 10, list_y + 10))

        for i, p_id in enumerate(data['available_parts_ids']):
            bx = self.col2_x + 15
            by = list_y + 40 + i * 35
            
            is_focus = (data['state'] == "part_list_select" and data['part_list_idx'] == i)
            if is_focus:
                pygame.draw.rect(self.screen, (60, 80, 100), (bx - 5, by - 2, self.col2_w - 30, 28))
                pygame.draw.rect(self.screen, COLORS['SELECT_HIGHLIGHT'], (bx - 5, by - 2, 5, 28))
            
            p_name = mgr.get_part_name(p_id)
            color = COLORS['TEXT'] if is_focus else (180, 180, 180)
            self.screen.blit(self.font.render(p_name, True, color), (bx + 10, by))

    def _draw_column_3(self, data):
        """詳細パラメータ"""
        self._draw_panel(self.col3_x, self.col3_w, "パーツ詳細")
        
        pd = data['focused_part_data']
        if not pd: return

        # 名前
        name_surf = self.font_bold.render(pd.get('name', '---'), True, COLORS['SELECT_HIGHLIGHT'])
        self.screen.blit(name_surf, (self.col3_x + 15, self.y + 50))
        
        # 各種パラメータ
        stats = [
            ("装甲", pd.get('hp', 0)),
            ("威力", pd.get('attack', '---')),
            ("推進", "--- (未実装)"),
            ("機動", "--- (未実装)"),
            ("防御", "--- (未実装)"),
            ("安定", "--- (未実装)")
        ]
        
        for i, (label, val) in enumerate(stats):
            by = self.y + 100 + i * 40
            pygame.draw.line(self.screen, (50, 60, 75), (self.col3_x + 15, by + 30), (self.col3_x + self.col3_w - 15, by + 30))
            
            l_surf = self.font.render(label, True, (150, 160, 180))
            self.screen.blit(l_surf, (self.col3_x + 15, by + 5))
            
            v_surf = self.font_bold.render(str(val), True, COLORS['TEXT'])
            vr = v_surf.get_rect(right=self.col3_x + self.col3_w - 20, top=by + 5)
            self.screen.blit(v_surf, vr)