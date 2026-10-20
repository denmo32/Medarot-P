"""カスタマイズ画面専用のレンダラー（テーマ色適用）"""
from typing import Optional
import pygame

from ui_base.renderer import BaseRenderer
from features.customize.ui.config import CUSTOMIZE_UI_PARAMS
from features.customize.ui.layout import calculate_customize_layout
from features.customize.presentation.view_models import CustomizeViewModel
from domain.constants import CustomizeState


class CustomizeRenderer(BaseRenderer):
    """カスタマイズ画面の3カラムレイアウトを描画"""

    def calc_layout(self, model: Optional[CustomizeViewModel] = None) -> dict:
        return calculate_customize_layout(self.get_screen_size(), model)

    def render(self, model: CustomizeViewModel):
        self.clear()
        layout = self.calc_layout(model)
        self._draw_column_1(model, layout)
        self._draw_column_2(model, layout)
        self._draw_column_3(model, layout)
        self.present()

    def _draw_panel_base(self, col_idx: int, title: str, layout: dict) -> int:
        col = layout['cols'][col_idx]
        rect = (col['x'], layout['y'], col['w'], layout['height'])
        self.draw_box(rect, self.theme.panel_bg, self.theme.panel_border)

        cfg = CUSTOMIZE_UI_PARAMS
        title_x = self.scaled(cfg['COLUMN_1_ITEM_PADDING'])
        title_y = self.scaled(cfg['COLUMN_1_ITEM_PADDING'])
        self.draw_text(title, (col['x'] + title_x, layout['y'] + title_y), (150, 160, 180), 'normal')

        line_y = layout['content_start_y']
        line_x_end = self.scaled(cfg['COLUMN_1_ITEM_PADDING'])
        pygame.draw.line(
            self.screen, self.theme.panel_border,
            (col['x'] + line_x_end, line_y),
            (col['x'] + col['w'] - line_x_end, line_y),
        )
        return line_y

    def _draw_column_1(self, model: CustomizeViewModel, layout: dict):
        self._draw_panel_base(0, "機体選択", layout)
        cfg = CUSTOMIZE_UI_PARAMS
        text_offset_x = self.scaled(cfg['COLUMN_1_TEXT_OFFSET_X'])

        for i, name in enumerate(model.robot_names):
            rect = layout['robot_rects'][i]
            if model.selected_robot_idx == i and model.state == CustomizeState.ROBOT_SELECT:
                pygame.draw.rect(self.screen, self.theme.select_highlight, rect)
            self.draw_text(name, (rect.x + text_offset_x, rect.y + rect.height // 4), self.theme.text, 'medium')

    def _draw_column_2(self, model: CustomizeViewModel, layout: dict):
        self._draw_panel_base(1, model.active_robot_name, layout)
        col = layout['cols'][1]
        cfg = CUSTOMIZE_UI_PARAMS
        text_offset_x = self.scaled(cfg['COLUMN_2_TEXT_OFFSET_X'])
        part_name_offset_x = self.scaled(cfg['COLUMN_2_PART_NAME_OFFSET_X'])
        list_title_offset_y = self.scaled(cfg['COLUMN_2_LIST_TITLE_OFFSET_Y'])
        list_highlight_w = self.scaled(cfg['COLUMN_2_LIST_HIGHLIGHT_WIDTH'])
        list_item_offset_x = self.scaled(cfg['COLUMN_2_LIST_ITEM_OFFSET_X'])

        # スロット情報
        for i, slot in enumerate(model.slots):
            rect = layout['slot_rects'][i]
            if slot.is_selected:
                pygame.draw.rect(self.screen, self.theme.select_highlight, rect)
            self.draw_text(slot.label, (rect.x + text_offset_x, rect.y + rect.height // 4), (180, 190, 200))
            self.draw_text(slot.part_name, (rect.x + part_name_offset_x, rect.y + rect.height // 4))

        # リスト区切り線・タイトル
        list_start_y = layout['list_start_y']
        pygame.draw.line(
            self.screen, self.theme.panel_border,
            (col['x'] + text_offset_x, list_start_y),
            (col['x'] + col['w'] - text_offset_x, list_start_y),
        )
        self.draw_text(
            "パーツ一覧",
            (col['x'] + text_offset_x, list_start_y + list_title_offset_y),
            (150, 160, 180),
        )

        # リストアイテム
        for i, item in enumerate(model.part_list):
            if i >= len(layout['part_list_rects']):
                break
            rect = layout['part_list_rects'][i]
            if item.is_focused:
                pygame.draw.rect(self.screen, self.theme.part_list_row_bg, rect)
                pygame.draw.rect(self.screen, self.theme.select_highlight, (rect.x, rect.y, list_highlight_w, rect.height))

            color = self.theme.text if item.is_focused else self.theme.part_list_dim
            self.draw_text(item.name, (col['x'] + list_item_offset_x, rect.y + self.scaled(2)), color)

    def _draw_column_3(self, model: CustomizeViewModel, layout: dict):
        detail = model.detail
        if not detail:
            return

        start_y = self._draw_panel_base(2, detail.title, layout)
        col = layout['cols'][2]

        cfg = CUSTOMIZE_UI_PARAMS
        title_offset_x = self.scaled(cfg['COLUMN_3_TITLE_OFFSET_X'])
        info_offset_y = self.scaled(cfg['COLUMN_3_INFO_START_OFFSET_Y'])
        row_label_offset_x = self.scaled(cfg['COLUMN_3_ROW_LABEL_OFFSET_X'])
        row_value_offset_x = self.scaled(cfg['COLUMN_3_ROW_VALUE_OFFSET_X'])
        row_line_offset_y = self.scaled(cfg['COLUMN_3_ROW_LINE_OFFSET_Y'])
        row_h = self.scale_y(cfg['COLUMN_3_ROW_HEIGHT_RATIO'])
        section_gap = self.scale_y(cfg['COLUMN_3_SECTION_GAP_RATIO'])

        self.draw_text(detail.name, (col['x'] + title_offset_x, start_y + section_gap), self.theme.select_highlight, 'medium')

        info_start_y = start_y + section_gap + info_offset_y
        for i, stat in enumerate(detail.stats):
            by = info_start_y + i * row_h
            line_y = by + row_h - row_line_offset_y
            pygame.draw.line(
                self.screen, (50, 60, 75),
                (col['x'] + row_label_offset_x, line_y),
                (col['x'] + col['w'] - row_label_offset_x, line_y),
            )
            self.draw_text(stat.label, (col['x'] + row_label_offset_x, by + self.scaled(5)), (150, 160, 180))
            self.draw_text(stat.value, (col['x'] + col['w'] - row_value_offset_x, by + self.scaled(5)),
                          self.theme.text, 'medium', 'right')