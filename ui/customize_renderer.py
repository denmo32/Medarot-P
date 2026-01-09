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
        
        names = ["機体1", "機体2", "機体3"]
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
        """中央：スロット構成 & アイテム一覧"""
        self._draw_panel(self.col2_x, self.col2_w, data['machine_name'])
        
        # 1. スロット構成
        slots = [
            ("medal", "メダル"), 
            ("head", "頭部"), 
            ("right_arm", "右腕"), 
            ("left_arm", "左腕"), 
            ("legs", "脚部")
        ]
        
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
            
            # ラベル
            l_surf = self.font.render(label, True, (180, 190, 200))
            self.screen.blit(l_surf, (bx + 10, by + 7))
            
            # 装着アイテム名
            if key == "medal":
                item_id = data['setup']['medal']
            else:
                item_id = data['setup']['parts'][key]
                
            item_name = mgr.get_part_name(item_id)
            n_surf = self.font.render(item_name, True, COLORS['TEXT'])
            self.screen.blit(n_surf, (bx + 100, by + 7))

        # 2. 一覧(下半分)
        list_y = self.y + 280
        pygame.draw.line(self.screen, COLORS['PANEL_BORDER'], (self.col2_x + 10, list_y), (self.col2_x + self.col2_w - 10, list_y))
        
        t_label = slots[data['slot_idx']][1]
        t_surf = self.font.render(f"{t_label}一覧", True, (150, 160, 180))
        self.screen.blit(t_surf, (self.col2_x + 10, list_y + 10))

        for i, item_id in enumerate(data['available_ids']):
            bx = self.col2_x + 15
            by = list_y + 40 + i * 35
            
            # はみ出し防止（簡易）
            if by > self.y + self.height - 30: break

            is_focus = (data['state'] == "part_list_select" and data['part_list_idx'] == i)
            if is_focus:
                pygame.draw.rect(self.screen, (60, 80, 100), (bx - 5, by - 2, self.col2_w - 30, 28))
                pygame.draw.rect(self.screen, COLORS['SELECT_HIGHLIGHT'], (bx - 5, by - 2, 5, 28))
            
            p_name = mgr.get_part_name(item_id)
            color = COLORS['TEXT'] if is_focus else (180, 180, 180)
            self.screen.blit(self.font.render(p_name, True, color), (bx + 10, by))

    def _draw_column_3(self, data):
        """詳細パラメータ"""
        title = "メダル詳細" if data['slot_idx'] == 0 else "パーツ詳細"
        self._draw_panel(self.col3_x, self.col3_w, title)
        
        fd = data['focused_data']
        if not fd: return

        # 名前
        name_surf = self.font_bold.render(fd.get('name', '---'), True, COLORS['SELECT_HIGHLIGHT'])
        self.screen.blit(name_surf, (self.col3_x + 15, self.y + 50))
        
        if data['slot_idx'] == 0:
            # メダルの詳細表示
            stats = [
                ("ニックネーム", fd.get('nickname', '---')),
                ("熟練度1", "--- (未実装)"),
                ("熟練度2", "--- (未実装)"),
                ("熟練度3", "--- (未実装)"),
                ("性格", "--- (未実装)")
            ]
        else:
            # パーツの詳細表示
            # 脚部以外ではmobility/defenseは存在しないので、getで対応
            stats = [
                ("装甲", fd.get('hp', 0)),
                ("威力", fd.get('attack', '---')),
                ("機動", fd.get('mobility', '---')),
                ("耐久", fd.get('defense', '---')),
            ]
        
        for i, (label, val) in enumerate(stats):
            by = self.y + 100 + i * 40
            pygame.draw.line(self.screen, (50, 60, 75), (self.col3_x + 15, by + 30), (self.col3_x + self.col3_w - 15, by + 30))
            
            l_surf = self.font.render(label, True, (150, 160, 180))
            self.screen.blit(l_surf, (self.col3_x + 15, by + 5))
            
            v_surf = self.font_bold.render(str(val), True, COLORS['TEXT'])
            vr = v_surf.get_rect(right=self.col3_x + self.col3_w - 20, top=by + 5)
            self.screen.blit(v_surf, vr)