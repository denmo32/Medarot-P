"""カスタマイズ画面のUIパラメータ定義"""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CustomizeUiParams:
    panel_padding_ratio: float = 0.02
    panel_y_ratio: float = 0.07
    panel_height_ratio: float = 0.86
    column_1_width_ratio: float = 0.22
    column_2_width_ratio: float = 0.38
    column_3_width_ratio: float = 0.32
    content_start_y_ratio: float = 0.06
    column_1_item_height_ratio: float = 0.07
    column_1_item_gap_ratio: float = 0.02
    column_1_item_padding: int = 10
    column_1_text_offset_x: int = 15
    column_2_item_height_ratio: float = 0.06
    column_2_item_gap_ratio: float = 0.015
    column_2_text_offset_x: int = 10
    column_2_part_name_offset_x: int = 80
    column_2_list_title_offset_y: int = 10
    column_2_list_start_padding: int = 40
    column_2_list_highlight_width: int = 5
    column_2_list_item_height_ratio: float = 0.05
    column_2_list_item_offset_x: int = 25
    column_2_list_indent: int = 30
    column_3_title_offset_x: int = 15
    column_3_info_start_offset_y: int = 40
    column_3_row_label_offset_x: int = 15
    column_3_row_value_offset_x: int = 20
    column_3_row_line_offset_y: int = 5
    column_3_row_height_ratio: float = 0.07
    column_3_section_gap_ratio: float = 0.03

    def __getitem__(self, item: str) -> Any:
        key = item.lower()
        return getattr(self, key)


CUSTOMIZE_UI_PARAMS = CustomizeUiParams()