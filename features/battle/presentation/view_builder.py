"""BattleManager の状態から表示専用モデル (BattleRenderModel) を生成する。UI色・UIパラメータへの依存を排除。"""
from typing import List, Optional, Sequence, TYPE_CHECKING
from domain.constants import (
    ALL_PART_TYPES,
    PART_TYPE_LABELS,
    AccentState,
    BadgeKind,
    EffectType,
    GaugeStatus,
    TeamType,
)
from features.battle.commands import PartCommand
from features.battle.constants import (
    BattlePhase,
    BattleTiming,
    TARGET_RADAR_PHASES,
    TARGET_RADAR_STATIC_PHASES,
)
from features.battle.input.command_menu_model import build_command_menu_items
from .view_models import (
    CommandMenuModel,
    BattleRenderModel,
    CutinActorModel,
    CutinModel,
    EffectBadgeModel,
    MessageWindowModel,
    OverlayModel,
    PartMiniHpModel,
    RobotStatusCardModel,
    RobotViewModel,
    TargetRadarModel,
    TopStatusPanelModel,
)

if TYPE_CHECKING:
    from features.battle.manager import BattleManager


def _resolve_accent_state(gauge_status: GaugeStatus, is_alive: bool, is_stopped: bool) -> AccentState:
    if is_stopped:
        return AccentState.STOPPED
    if not is_alive:
        return AccentState.NEUTRAL
    if gauge_status == GaugeStatus.CHARGING:
        return AccentState.CHARGING
    if gauge_status == GaugeStatus.COOLDOWN:
        return AccentState.COOLDOWN
    if gauge_status in (GaugeStatus.READY, GaugeStatus.EXECUTING):
        return AccentState.READY
    return AccentState.NEUTRAL


COMMAND_MENU_PHASES = (BattlePhase.INPUT,)
MESSAGE_WINDOW_PHASES = (
    BattlePhase.INITIAL_SETUP,
    BattlePhase.OPENING_LOG,
    BattlePhase.OPENING_POPUP,
    BattlePhase.IDLE,
    BattlePhase.TARGET_INDICATION,
    BattlePhase.ATTACK_DECLARATION,
    BattlePhase.CUTIN,
    BattlePhase.CUTIN_RESULT,
    BattlePhase.LOG_WAIT,
    BattlePhase.GAME_OVER,
)
CUTIN_PHASES = (BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT)


class BattleViewBuilder:
    def __init__(self, manager: 'BattleManager'):
        self.manager = manager

    def build(self, selected_button_index: int = 0) -> BattleRenderModel:
        ctx = self.manager.ctx
        phase = ctx.phase

        robots = self._build_robots()
        target_radar = self._build_target_radar()
        message_window = self._build_message_window()
        command_menu = self._build_command_menu(selected_button_index)
        cutin = self._build_cutin()
        overlay = self._build_overlay(phase)
        top_status = self._build_top_status()

        return BattleRenderModel(
            phase=phase,
            show_field=True,
            show_message_window=message_window is not None,
            show_command_menu=command_menu is not None,
            show_cutin=cutin is not None,
            show_opening_popup=overlay is not None and overlay.opening_popup_visible,
            show_game_over=overlay is not None and overlay.game_over_winner is not None,
            show_target_radar=target_radar is not None,
            show_preview_target_markers=bool(command_menu and command_menu.preview_target_robot_indices),
            robots=robots,
            target_radar=target_radar,
            message_window=message_window,
            command_menu=command_menu,
            cutin=cutin,
            overlay=overlay,
            top_status=top_status,
        )

    def _build_robots(self) -> List[RobotViewModel]:
        robots = self.manager.ctx.robots
        visual_states = self.manager.presentation.visual_states
        team_counts = {}
        for robot in robots:
            team_counts[robot.team] = team_counts.get(robot.team, 0) + 1

        team_indexes = {}
        views: List[RobotViewModel] = []

        for index, robot in enumerate(robots):
            team_index = team_indexes.get(robot.team, 0)
            team_indexes[robot.team] = team_index + 1
            visual_state = visual_states[robot]
            is_stopped = robot.is_stopped
            is_alive = visual_state.is_visually_alive

            views.append(RobotViewModel(
                index=index,
                team=robot.team,
                is_alive=is_alive,
                gauge_status=robot.gauge_status,
                is_stopped=is_stopped,
                accent_state=_resolve_accent_state(robot.gauge_status, is_alive, is_stopped),
                part_status=dict(visual_state.parts_break_progress),
                part_stopped={pt: robot.is_part_stopped(pt) for pt in ALL_PART_TYPES},
                progress_ratio=robot.position,
                team_index=team_index,
                team_count=team_counts[robot.team],
            ))
        return views

    def _build_top_status(self) -> TopStatusPanelModel:
        ctx = self.manager.ctx
        robots = ctx.robots
        combat_robots = set()
        if ctx.phase in CUTIN_PHASES:
            actor = ctx.current_actor
            report = ctx.current_report
            target = report.target if report else None
            if actor is not None and target is not None:
                combat_robots = {id(actor), id(target)}

        player_robots = [r for r in robots if r.team == TeamType.PLAYER]
        enemy_robots = [r for r in robots if r.team == TeamType.ENEMY]

        return TopStatusPanelModel(
            player_cards=[self._build_robot_card(i, r, id(r) in combat_robots) for i, r in enumerate(player_robots)],
            enemy_cards=[self._build_robot_card(i, r, id(r) in combat_robots) for i, r in enumerate(enemy_robots)],
        )

    def _build_robot_card(self, robot_index: int, robot, is_combat_active: bool = False) -> RobotStatusCardModel:
        visual_state = self.manager.presentation.visual_states[robot]
        is_alive = visual_state.is_visually_alive
        parts_hp: List[PartMiniHpModel] = []

        for part_type in ALL_PART_TYPES:
            part = robot.get_part(part_type)
            if not part:
                continue
            display_hp = float(visual_state.parts_display_hp.get(part_type, part.hp))
            max_hp = max(1, part.max_hp)
            parts_hp.append(PartMiniHpModel(
                part_type=part_type,
                label=PART_TYPE_LABELS.get(part_type, ""),
                current_hp=int(display_hp),
                max_hp=part.max_hp,
                ratio=max(0.0, min(1.0, display_hp / max_hp)),
                is_broken=display_hp <= 0,
                is_stopped=robot.is_part_stopped(part_type),
            ))

        display_name = f"{robot.name}[LEADER]" if robot.is_leader else robot.name
        return RobotStatusCardModel(
            robot_index=robot_index,
            name=display_name,
            team=robot.team,
            is_leader=robot.is_leader,
            is_alive=is_alive,
            accent_state=_resolve_accent_state(robot.gauge_status, is_alive, robot.is_stopped),
            target_text=self._build_target_text(robot),
            badges=self._build_effect_badges(robot),
            parts_hp=parts_hp,
            is_combat_active=is_combat_active,
        )

    def _build_target_text(self, robot) -> Optional[str]:
        if not robot.is_charging:
            return None
        command = robot.current_command
        if not isinstance(command, PartCommand):
            return None
        part = robot.current_part
        if not part:
            return None

        if command.target_robot:
            target_label = command.target_robot.name
            if command.target_part:
                target_label += f" [{PART_TYPE_LABELS.get(command.target_part, '')}]"
            return f"└> {target_label}"

        if not part.locks_target:
            return "└> 直前選定"
        return None

    def _build_effect_badges(self, robot) -> List[EffectBadgeModel]:
        badges: List[EffectBadgeModel] = []
        for effect in robot.active_effects:
            if effect.type == EffectType.STOP:
                text = "停止"
                if effect.part_type:
                    text += f" {PART_TYPE_LABELS.get(effect.part_type, '')}"
                text += f" {effect.duration:.1f}s"
                badges.append(EffectBadgeModel(text, BadgeKind.STOP))
            elif effect.type == EffectType.BLOCK:
                badges.append(EffectBadgeModel("護衛 (BLOCK)", BadgeKind.BLOCK))
            elif effect.type == EffectType.PROTECT:
                badges.append(EffectBadgeModel("自衛 (PROTECT)", BadgeKind.PROTECT))
            elif effect.type == EffectType.SUCCESS_UP:
                charges = effect.charges if effect.charges is not None else 1
                badges.append(EffectBadgeModel(f"命中+{effect.magnitude} ({charges}回)", BadgeKind.SUCCESS_UP))
        return badges

    def _build_target_radar(self) -> Optional[TargetRadarModel]:
        ctx = self.manager.ctx
        if ctx.phase not in TARGET_RADAR_PHASES:
            return None
        attacker = ctx.current_actor
        if not attacker or not attacker.is_alive:
            return None
        part = attacker.current_part
        if not part or not part.can_execute:
            return None
        report = ctx.current_report
        target = report.target if report else None
        if not target or not target.is_alive:
            return None

        attacker_index = _robot_index(ctx.robots, attacker)
        target_index = _robot_index(ctx.robots, target)
        if attacker_index is None or target_index is None:
            return None

        return TargetRadarModel(
            attacker_index=attacker_index,
            target_index=target_index,
            is_static=ctx.phase in TARGET_RADAR_STATIC_PHASES,
        )

    def _build_message_window(self) -> Optional[MessageWindowModel]:
        ctx = self.manager.ctx
        if ctx.phase not in MESSAGE_WINDOW_PHASES:
            return None
        max_lines = BattleTiming.LOG_DISPLAY_MAX
        return MessageWindowModel(
            lines=list(ctx.battle_log[-max_lines:]),
            show_advance_marker=self.manager.is_waiting_for_advance(),
        )

    def _build_command_menu(self, selected_button_index: int) -> Optional[CommandMenuModel]:
        ctx = self.manager.ctx
        if ctx.phase not in COMMAND_MENU_PHASES or not ctx.current_actor:
            return None

        items = build_command_menu_items(ctx.current_actor, ctx.preview_targets, ctx.robots)
        if not items:
            return None

        selected = selected_button_index if 0 <= selected_button_index < len(items) else 0
        selected_item = items[selected]

        preview_indices = []
        if selected_item.preview_target_robot_index is not None:
            preview_indices.append(selected_item.preview_target_robot_index)

        return CommandMenuModel(
            actor_name=ctx.current_actor.name,
            selected_index=selected,
            items=items,
            preview_target_robot_indices=preview_indices,
        )

    def _build_cutin(self) -> Optional[CutinModel]:
        ctx = self.manager.ctx
        director = self.manager.presentation.cutin_director
        if ctx.phase not in CUTIN_PHASES or director is None:
            return None
        actor = ctx.current_actor
        report = ctx.current_report
        if not (actor and report and report.target):
            return None

        visual_states = self.manager.presentation.visual_states
        actor_model = _build_cutin_actor(actor, visual_states[actor])
        target_model = _build_cutin_actor(report.target, visual_states[report.target])

        return director.build_cutin_model(actor_model, target_model)

    def _build_overlay(self, phase: BattlePhase) -> Optional[OverlayModel]:
        if phase == BattlePhase.OPENING_POPUP:
            return OverlayModel(opening_popup_visible=True)
        if phase == BattlePhase.GAME_OVER:
            return OverlayModel(game_over_winner=self.manager.ctx.winner)
        return None


def _build_cutin_actor(robot, visual_state) -> CutinActorModel:
    is_alive = visual_state.is_visually_alive
    return CutinActorModel(
        team=robot.team,
        part_status=dict(visual_state.parts_break_progress),
        accent_state=_resolve_accent_state(robot.gauge_status, is_alive, robot.is_stopped),
    )


def _robot_index(robots: Sequence, robot) -> Optional[int]:
    for index, candidate in enumerate(robots):
        if candidate is robot:
            return index
    return None