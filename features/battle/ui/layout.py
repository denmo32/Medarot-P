"""バトル画面の座標・矩形計算。"""
from typing import TYPE_CHECKING, List, Optional, Tuple
import pygame

from domain.constants import (
    COMMAND_MENU_HEAD_INDEX,
    COMMAND_MENU_LEFT_ARM_INDEX,
    COMMAND_MENU_RIGHT_ARM_INDEX,
    TeamType,
)
from ui_base.interaction import handle_menu_mouse
from ui_base.config import SCREEN_HEIGHT
from features.battle.ui.config import BATTLE_UI_PARAMS as UI_PARAMS

if TYPE_CHECKING:
    from features.battle.presentation.view_models import RobotViewModel, CutinActorModel


def _ui_scale(screen_size: Tuple[int, int]) -> float:
    return screen_size[1] / SCREEN_HEIGHT


def _scaled(value: float, screen_size: Tuple[int, int]) -> int:
    return int(value * _ui_scale(screen_size))


def _scale_x(ratio: float, screen_size: Tuple[int, int]) -> int:
    return int(ratio * screen_size[0])


def _scale_y(ratio: float, screen_size: Tuple[int, int]) -> int:
    return int(ratio * screen_size[1])


def _to_px(rx: float, ry: float, screen_size: Tuple[int, int]) -> Tuple[int, int]:
    return int(rx * screen_size[0]), int(ry * screen_size[1])


def _is_player(team: TeamType) -> bool:
    return team == TeamType.PLAYER


# === フィールド系 ===

def calculate_field_top_y(screen_size: Tuple[int, int]) -> int:
    return _scale_y(UI_PARAMS.battlefield_y_start_ratio, screen_size)


def calculate_field_bottom_y(screen_size: Tuple[int, int]) -> int:
    return _scale_y(UI_PARAMS.battlefield_y_end_ratio, screen_size)


def calculate_field_background_rect(screen_size: Tuple[int, int]) -> pygame.Rect:
    top_y = calculate_field_top_y(screen_size)
    bottom_y = calculate_field_bottom_y(screen_size)
    return pygame.Rect(0, top_y, screen_size[0], bottom_y - top_y)


def calculate_top_status_layout(screen_size: Tuple[int, int]) -> dict:
    sw, sh = screen_size
    top_area_h = calculate_field_top_y(screen_size)

    margin_x = _scaled(8, screen_size)
    margin_y = _scaled(4, screen_size)
    gap_x = _scaled(10, screen_size)
    panel_h = top_area_h - margin_y * 2
    panel_w = (sw - margin_x * 2 - gap_x) // 2

    left_panel_rect = pygame.Rect(margin_x, margin_y, panel_w, panel_h)
    right_panel_rect = pygame.Rect(margin_x + panel_w + gap_x, margin_y, panel_w, panel_h)

    card_pad_x = _scaled(4, screen_size)
    card_pad_y = _scaled(4, screen_size)
    card_gap = _scaled(4, screen_size)

    card_area_y = margin_y + card_pad_y
    card_h = panel_h - card_pad_y * 2
    card_w = (panel_w - card_pad_x * 2 - card_gap * 2) // 3

    def make_card_rects(panel_rect: pygame.Rect):
        return [
            pygame.Rect(
                panel_rect.x + card_pad_x + i * (card_w + card_gap),
                card_area_y,
                card_w,
                card_h,
            )
            for i in range(3)
        ]

    return {
        'left_panel_rect': left_panel_rect,
        'right_panel_rect': right_panel_rect,
        'left_card_rects': make_card_rects(left_panel_rect),
        'right_card_rects': make_card_rects(right_panel_rect),
    }


def calculate_guide_line_xs(screen_size: Tuple[int, int]) -> List[int]:
    center_x = screen_size[0] // 2
    offset = _scale_x(UI_PARAMS.guide_line_offset_ratio, screen_size)
    return [center_x - offset, center_x + offset]


# === ロボット系 ===

def calculate_robot_y_ratio(team_index: int, team_count: int) -> float:
    start_y = UI_PARAMS.battlefield_y_start_ratio
    end_y = UI_PARAMS.battlefield_y_end_ratio
    height = end_y - start_y

    if team_count <= 0:
        return start_y

    return start_y + (team_index + UI_PARAMS.robot_y_padding) * (height / team_count)


def calculate_robot_position(
    robot: 'RobotViewModel',
    screen_size: Tuple[int, int],
) -> Tuple[int, int]:
    y_ratio = calculate_robot_y_ratio(robot.team_index, robot.team_count)
    is_player = _is_player(robot.team)
    team_x_ratio = (UI_PARAMS.player_team_x_ratio if is_player
                    else UI_PARAMS.enemy_team_x_ratio)
    margin = UI_PARAMS.team_boundary_margin_ratio
    progress_ratio = robot.progress_ratio

    if is_player:
        end_x = 0.5 - margin
        icon_x_ratio = team_x_ratio + progress_ratio * (end_x - team_x_ratio)
    else:
        start_x = team_x_ratio + UI_PARAMS.gauge_width_ratio
        end_x = 0.5 + margin
        icon_x_ratio = start_x + progress_ratio * (end_x - start_x)

    return _to_px(icon_x_ratio, y_ratio, screen_size)


def calculate_home_marker_rect(
    robot: 'RobotViewModel',
    screen_size: Tuple[int, int],
) -> pygame.Rect:
    marker_rx = _scaled(UI_PARAMS.home_marker_rx, screen_size)
    marker_ry = _scaled(UI_PARAMS.home_marker_ry, screen_size)

    team_x_ratio = (UI_PARAMS.player_team_x_ratio if _is_player(robot.team)
                    else UI_PARAMS.enemy_team_x_ratio + UI_PARAMS.gauge_width_ratio)
    hx, hy = _to_px(
        team_x_ratio,
        calculate_robot_y_ratio(robot.team_index, robot.team_count),
        screen_size,
    )

    return pygame.Rect(
        hx - marker_rx,
        hy + _scaled(20, screen_size) - marker_ry,
        marker_rx * 2,
        marker_ry * 2,
    )


# === メッセージ系 ===

def calculate_message_window_rect(screen_size: Tuple[int, int]) -> pygame.Rect:
    sw, sh = screen_size
    wy = _scale_y(UI_PARAMS.message_window_y_ratio, screen_size)
    wh = _scale_y(UI_PARAMS.message_window_height_ratio, screen_size)
    return pygame.Rect(0, wy, sw, wh)


def calculate_message_padding(screen_size: Tuple[int, int]) -> int:
    return _scale_x(UI_PARAMS.message_window_padding_ratio, screen_size)


def calculate_log_line_height(screen_size: Tuple[int, int]) -> int:
    return _scaled(UI_PARAMS.log_line_height, screen_size)


# === コマンドメニュー系 ===

def calculate_command_menu_rects(
    button_count: int,
    screen_size: Tuple[int, int],
) -> List[pygame.Rect]:
    sw, sh = screen_size

    btn_w = int(sw * UI_PARAMS.btn_width_ratio)
    btn_h = int(sh * UI_PARAMS.btn_height_ratio)
    btn_pad = int(sw * UI_PARAMS.btn_padding_ratio)
    wy_ratio = UI_PARAMS.message_window_y_ratio

    start_y = int(sh * wy_ratio) + int(sh * UI_PARAMS.command_menu_top_padding_ratio)
    center_x = sw // 2

    rects: List[pygame.Rect] = []
    for i in range(button_count):
        rect = pygame.Rect(0, 0, btn_w, btn_h)
        if i == COMMAND_MENU_HEAD_INDEX:
            rect.centerx = center_x
            rect.top = start_y
        elif i == COMMAND_MENU_RIGHT_ARM_INDEX:
            rect.right = center_x - (btn_pad // 2)
            rect.top = start_y + btn_h + btn_pad
        elif i == COMMAND_MENU_LEFT_ARM_INDEX:
            rect.left = center_x + (btn_pad // 2)
            rect.top = start_y + btn_h + btn_pad
        else:
            rect.left = center_x + btn_w + btn_pad * 2
            rect.centery = start_y + btn_h + (btn_pad // 2)
        rects.append(rect)

    return rects


def calculate_action_label_position(screen_size: Tuple[int, int]) -> Tuple[int, int]:
    pad = calculate_message_padding(screen_size)
    wy = _scale_y(UI_PARAMS.message_window_y_ratio, screen_size)
    return pad, wy + pad + int(screen_size[1] * UI_PARAMS.action_name_y_ratio)


# === カットイン系 ===

def calculate_cutin_layout(screen_size: Tuple[int, int]) -> dict:
    sw, sh = screen_size
    top_y = calculate_field_top_y(screen_size)
    bottom_y = calculate_field_bottom_y(screen_size)
    return {
        'panel_rect': pygame.Rect(0, top_y, sw, bottom_y - top_y),
        'center_y': (top_y + bottom_y) // 2,
        'left_x': int(sw * UI_PARAMS.cutin_left_ratio),
        'right_x': int(sw * UI_PARAMS.cutin_right_ratio),
    }


def calculate_cutin_actor_positions(
    actor_team: TeamType,
    screen_size: Tuple[int, int],
) -> Tuple[int, int]:
    cutin_layout = calculate_cutin_layout(screen_size)
    if _is_player(actor_team):
        return cutin_layout['left_x'], cutin_layout['right_x']
    return cutin_layout['right_x'], cutin_layout['left_x']


def calculate_cutin_actor_x(
    actor_model: 'CutinActorModel',
    screen_size: Tuple[int, int],
) -> int:
    actor_x, target_x = calculate_cutin_actor_positions(actor_model.team, screen_size)
    motion = actor_model.motion
    if motion is None:
        return actor_x

    sw, _ = screen_size
    contact_offset = _scaled(UI_PARAMS.cutin_melee_contact_offset, screen_size)
    exit_margin = _scaled(UI_PARAMS.cutin_melee_exit_margin, screen_size)

    if _is_player(actor_model.team):
        contact_x = target_x - contact_offset
        exit_x = sw + exit_margin
    else:
        contact_x = target_x + contact_offset
        exit_x = -exit_margin

    if motion.phase == "approach":
        return int(actor_x + (contact_x - actor_x) * motion.progress)
    elif motion.phase == "pass_through":
        return int(contact_x + (exit_x - contact_x) * motion.progress)

    return actor_x


def calculate_cutin_scrolled_positions(
    actor_team: TeamType,
    camera_progress: float,
    screen_size: Tuple[int, int],
) -> Tuple[int, int]:
    sw, _ = screen_size
    base_actor_x, base_target_x = calculate_cutin_actor_positions(actor_team, screen_size)
    scroll_distance = int(sw * 0.5)

    if _is_player(actor_team):
        actor_x = int(base_actor_x - camera_progress * scroll_distance)
        target_x = int(base_target_x + (1.0 - camera_progress) * scroll_distance)
    else:
        actor_x = int(base_actor_x + camera_progress * scroll_distance)
        target_x = int(base_target_x - (1.0 - camera_progress) * scroll_distance)

    return actor_x, target_x


def calculate_cutin_projectile_x(
    progress: float,
    actor_team: TeamType,
    camera_progress: Optional[float],
    screen_size: Tuple[int, int],
) -> int:
    sw, _ = screen_size
    base_actor_x, base_target_x = calculate_cutin_actor_positions(actor_team, screen_size)

    if camera_progress is None:
        return int(base_actor_x + (base_target_x - base_actor_x) * progress)

    scroll_distance = sw * 0.5
    if _is_player(actor_team):
        total_dist = (base_target_x + scroll_distance) - base_actor_x
        world_x = base_actor_x + progress * total_dist
        cam_offset = camera_progress * scroll_distance
        return int(world_x - cam_offset)
    else:
        total_dist = base_actor_x - (base_target_x - scroll_distance)
        world_x = base_actor_x - progress * total_dist
        cam_offset = camera_progress * scroll_distance
        return int(world_x + cam_offset)


def hit_test_command_menu(
    screen_size: Tuple[int, int],
    mouse_pos: Tuple[int, int],
    item_count: int,
    current_index: int,
) -> Tuple[int, bool]:
    layouts = calculate_command_menu_rects(item_count, screen_size)
    return handle_menu_mouse(mouse_pos, True, layouts, current_index)