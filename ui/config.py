"""UI関連の設定値とテーマ定義"""

from dataclasses import dataclass, field
from typing import Any, Tuple

from domain.constants import AccentState

Color = Tuple[int, int, int]
AlphaColor = Tuple[int, int, int, int]

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 600


@dataclass(frozen=True)
class Theme:
    """型安全なUIテーマカラーパレット"""
    background: Color = (50, 50, 50)
    player: Color = (0, 100, 200)
    enemy: Color = (200, 0, 0)
    text: Color = (255, 255, 255)
    notice_bg: AlphaColor = (0, 0, 0, 180)
    button_bg: Color = (150, 150, 150)
    button_disabled_bg: Color = (80, 80, 80)
    button_border: Color = (0, 0, 0)

    # コマンド選択ボタン
    cmd_menu_bg: Color = (5, 5, 40)
    cmd_btn_normal_bg: Color = (60, 80, 220)
    cmd_btn_focus_bg: Color = (120, 255, 50)
    action_label_text: Color = (200, 255, 100)

    # フィールド
    guide_line: Color = (120, 120, 120)
    home_marker: Color = (100, 100, 100)
    panel_bg: Color = (35, 45, 60)
    panel_border: Color = (60, 70, 90)
    select_highlight: Color = (0, 150, 255)
    part_list_dim: Color = (180, 180, 180)
    part_list_row_bg: Color = (60, 80, 100)

    # メッセージウィンドウ (パイプ装飾)
    msg_bg: Color = (225, 195, 64)
    msg_pipe: Color = (180, 60, 20)
    msg_joint: Color = (100, 30, 10)
    msg_text: Color = (0, 0, 0)

    # 演出
    field_bg: Color = (40, 45, 55)
    cutin_bg: AlphaColor = (0, 0, 0, 180)
    stop_effect: Color = (255, 255, 0)
    target_radar: Color = (0, 240, 255)
    target_marker: Color = (255, 255, 0)
    bullet: Color = (255, 230, 80)
    bullet_core: Color = (255, 255, 255)

    # ステータスパネル
    status_panel_bg: Color = (22, 26, 35)
    status_panel_border: Color = (50, 62, 80)
    status_card_bg: Color = (32, 38, 50)
    status_card_dead_bg: Color = (22, 25, 32)
    status_card_border: Color = (50, 62, 80)
    status_card_dim: AlphaColor = (0, 0, 0, 120)
    status_card_dead_text: Color = (130, 130, 140)
    status_target_text: Color = (170, 200, 230)
    status_part_label: Color = (200, 205, 215)
    status_part_num: Color = (210, 215, 225)
    hp_bg: Color = (80, 0, 0)
    hp_border: Color = (60, 60, 70)
    badge_stop_bg: Color = (230, 190, 30)
    badge_stop_text: Color = (0, 0, 0)
    badge_stance_bg: Color = (40, 140, 220)
    badge_buff_bg: Color = (50, 180, 120)
    hp_safe: Color = (60, 220, 100)
    hp_warn: Color = (230, 180, 40)
    hp_danger: Color = (230, 60, 60)
    hp_broken_text: Color = (140, 70, 70)

    # 機体アイコン・状態色
    icon_charging: Color = (255, 150, 40)
    icon_cooldown: Color = (80, 160, 255)
    icon_ready: Color = (80, 220, 120)
    icon_neutral: Color = (170, 175, 195)
    icon_stopped: Color = (60, 60, 60)


DEFAULT_THEME = Theme()


def resolve_accent_color(state: AccentState, theme: Theme = DEFAULT_THEME) -> Color:
    """機体・パーツの状態アクセント（充填中/放熱中/停止など）をテーマ色へ変換する。"""
    mapping = {
        AccentState.CHARGING: theme.icon_charging,
        AccentState.COOLDOWN: theme.icon_cooldown,
        AccentState.READY: theme.icon_ready,
        AccentState.STOPPED: theme.icon_stopped,
        AccentState.NEUTRAL: theme.icon_neutral,
    }
    return mapping.get(state, theme.icon_neutral)


FONT_NAMES = ['assets/fonts/NotoSansJP-Regular.ttf']
COMMAND_BUTTON_FONT_NAME = 'assets/fonts/851Gkktt_005.ttf'

# ==============================================================================
# 型安全な UI レイアウトパラメータ定義
# ==============================================================================

@dataclass(frozen=True)
class CommandButtonUiParams:
    btn_width_ratio: float = 0.25
    btn_height_ratio: float = 0.075
    btn_padding_ratio: float = 0.012

    def __getitem__(self, item: str) -> Any:
        mapping = {
            'BTN_WIDTH_RATIO': self.btn_width_ratio,
            'BTN_HEIGHT_RATIO': self.btn_height_ratio,
            'BTN_PADDING_RATIO': self.btn_padding_ratio,
        }
        return mapping[item]


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


@dataclass(frozen=True)
class UiParams:
    """UI の比率・マージン・ピクセル規定（イミュータブル・辞書互換アクセス両対応）"""
    battlefield_y_start_ratio: float = 0.25
    battlefield_y_end_ratio: float = 0.75
    player_team_x_ratio: float = 0.06
    enemy_team_x_ratio: float = 0.56
    gauge_width_ratio: float = 0.38
    team_boundary_margin_ratio: float = 0.05
    guide_line_offset_ratio: float = 0.05
    robot_y_padding: float = 0.5
    home_marker_rx: int = 24
    home_marker_ry: int = 10
    robot_icon_scale: float = 0.4
    target_marker_offset: int = 4
    message_window_y_ratio: float = 0.75
    message_window_height_ratio: float = 0.25
    message_window_padding_ratio: float = 0.012
    log_line_height: int = 25
    blink_interval_ms: int = 500
    advance_marker_size: int = 8
    command_menu_top_padding_ratio: float = 0.04
    action_name_y_ratio: float = 0.05
    cutin_left_ratio: float = 0.25
    cutin_right_ratio: float = 0.75
    cutin_label_offset: int = 80
    cutin_damage_offset: int = 50
    cutin_popup_threshold: float = 1.0
    cutin_projectile_radius: int = 7
    cutin_melee_contact_offset: int = 50
    cutin_melee_exit_margin: int = 80
    target_radar_size: int = 56
    target_radar_corner_len: int = 12
    target_radar_travel_sec: float = 0.3
    target_radar_pulse_sec: float = 0.22
    ui: CommandButtonUiParams = field(default_factory=CommandButtonUiParams)
    customize: CustomizeUiParams = field(default_factory=CustomizeUiParams)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key: str) -> Any:
        attr = key.lower()
        if hasattr(self, attr):
            return getattr(self, attr)
        raise KeyError(key)


UI_PARAMS = UiParams()