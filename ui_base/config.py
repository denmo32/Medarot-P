"""UI基盤の共通設定値とテーマ定義"""

from dataclasses import dataclass
from typing import Tuple

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