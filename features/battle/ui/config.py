"""バトル画面のUIパラメータ定義"""
from dataclasses import dataclass

COMMAND_BUTTON_FONT_NAME = 'assets/fonts/851Gkktt_005.ttf'


@dataclass(frozen=True)
class BattleUiParams:
    """バトル画面の比率・マージン・ピクセル規定（不変データモデル）"""
    # フィールド
    battlefield_y_start_ratio: float = 0.25
    battlefield_y_end_ratio: float = 0.75
    player_team_x_ratio: float = 0.06
    enemy_team_x_ratio: float = 0.56
    gauge_width_ratio: float = 0.38
    team_boundary_margin_ratio: float = 0.05
    guide_line_offset_ratio: float = 0.05

    # ロボット・マーカー
    robot_y_padding: float = 0.5
    home_marker_rx: int = 24
    home_marker_ry: int = 10
    robot_icon_scale: float = 0.4
    target_marker_offset: int = 4

    # メッセージウィンドウ
    message_window_y_ratio: float = 0.75
    message_window_height_ratio: float = 0.25
    message_window_padding_ratio: float = 0.012
    log_line_height: int = 25
    blink_interval_ms: int = 500
    advance_marker_size: int = 8

    # コマンドメニュー（3段配置に合わせて高さを0.075→0.055に調整）
    command_menu_top_padding_ratio: float = 0.02
    action_name_y_ratio: float = 0.04
    btn_width_ratio: float = 0.22
    btn_height_ratio: float = 0.055
    btn_padding_ratio: float = 0.008

    # カットイン演出
    cutin_left_ratio: float = 0.25
    cutin_right_ratio: float = 0.75
    cutin_label_offset: int = 80
    cutin_damage_offset: int = 50
    cutin_projectile_radius: int = 7
    cutin_melee_contact_offset: int = 50
    cutin_melee_exit_margin: int = 80

    # ターゲットレーダー
    target_radar_size: int = 56
    target_radar_corner_len: int = 12


BATTLE_UI_PARAMS = BattleUiParams()