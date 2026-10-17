"""BattleContext および VisualCoordinator から表示専用モデル (BattleRenderModel) を生成する。"""
import dataclasses
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
from domain.models import ActionResult
from features.battle.commands import PartCommand
from features.battle.constants import (
    BattlePhase,
    BattleTiming,
    CutinStep,
    TARGET_RADAR_PHASES,
    TARGET_RADAR_STATIC_PHASES,
)
from .command_menu_builder import build_command_menu_items
from .view_models import (
    CommandMenuModel,
    BattleRenderModel,
    CutinActorModel,
    CutinModel,
    CutinPopupModel,
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
    from features.battle.context import BattleContext
    from features.battle.cutin_director import CutinDirector
    from features.battle.visual_coordinator import VisualCoordinator

CUTIN_POPUP_LABELS = {
    "critical": "CRITICAL!!",
    "guard": "GUARD",
    "hit": "HIT!",
    "miss": "MISS!",
    "pierce": "PENETRATION",
}


def _resolve_cutin_popup(result: ActionResult, step: CutinStep) -> CutinPopupModel:
    if step == CutinStep.PIERCE:
        pierce = result.pierce_effect
        dmg = pierce.effective_damage if pierce else 0
        return CutinPopupModel(
            primary_label=CUTIN_POPUP_LABELS["pierce"],
            damage_label=f"-{dmg}",
            is_miss=False,
        )

    if not result.success:
        return CutinPopupModel(
            primary_label="",
            damage_label=CUTIN_POPUP_LABELS["miss"],
            is_miss=True,
        )

    if result.is_critical:
        label = CUTIN_POPUP_LABELS["critical"]
    elif result.is_guarded:
        label = CUTIN_POPUP_LABELS["guard"]
    else:
        label = CUTIN_POPUP_LABELS["hit"]

    return CutinPopupModel(
        primary_label=label,
        damage_label=f"-{result.effective_damage}",
        is_miss=False,
    )


def _build_cutin_model(
    director: 'CutinDirector',
    actor_model: CutinActorModel,
    target_model: CutinActorModel,
) -> CutinModel:
    profile = director.profile
    elapsed = director.elapsed
    step = director.step
    result = director.result

    camera_progress: Optional[float] = None
    if profile.camera_track is not None:
        camera_progress = profile.camera_track.evaluate(elapsed)

    if step == CutinStep.PIERCE or director.is_result_shown:
        if profile.actor_movement is not None:
            actor_model = dataclasses.replace(actor_model, is_visible=False, motion=None)
        elif profile.camera_track is not None:
            camera_progress = 1.0
            actor_model = dataclasses.replace(actor_model, is_visible=False)

        return CutinModel(
            actor=actor_model,
            target=target_model,
            popup=_resolve_cutin_popup(result, step),
            projectiles=[],
            impacts=[],
            camera_progress=camera_progress,
        )

    is_hit = result.success

    if profile.actor_movement is not None:
        is_visible, motion = profile.actor_movement.evaluate(elapsed)
        actor_model = dataclasses.replace(actor_model, is_visible=is_visible, motion=motion)
    elif camera_progress is not None:
        is_visible = camera_progress < 1.0
        actor_model = dataclasses.replace(actor_model, is_visible=is_visible)

    projectiles = [
        p for track in profile.projectiles
        if (p := track.evaluate(elapsed, is_hit)) is not None
    ]
    impacts = [
        i for track in profile.impacts
        if (i := track.evaluate(elapsed, is_hit)) is not None
    ]

    show_popup = director.is_animation_finished or profile.popup.is_active(elapsed, is_hit)
    popup = _resolve_cutin_popup(result, step) if show_popup else None

    return CutinModel(
        actor=actor_model,
        target=target_model,
        popup=popup,
        projectiles=projectiles,
        impacts=impacts,
        camera_progress=camera_progress,
    )


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
    """戦闘状態（Context）と演出状態（Visual）から描画用モデルを一括生成するプロジェクター"""

    def __init__(self, ctx: 'BattleContext', visual: 'VisualCoordinator'):
        self.ctx = ctx
        self.visual = visual

    def build(self, selected_button_index: int = 0) -> BattleRenderModel:
        phase = self.ctx.phase

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
        robots = self.ctx.robots
        visual_states = self.visual.visual_states
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
        robots = self.ctx.robots
        combat_robots = set()
        if self.ctx.phase in CUTIN_PHASES:
            actor = self.ctx.current_actor
            report = self.ctx.current_report
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
        visual_state = self.visual.visual_states[robot]
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
        if self.ctx.phase not in TARGET_RADAR_PHASES:
            return None
        attacker = self.ctx.current_actor
        if not attacker or not attacker.is_alive:
            return None
        part = attacker.current_part
        if not part or not part.can_execute:
            return None
        report = self.ctx.current_report
        target = report.target if report else None
        if not target or not target.is_alive:
            return None

        attacker_index = _robot_index(self.ctx.robots, attacker)
        target_index = _robot_index(self.ctx.robots, target)
        if attacker_index is None or target_index is None:
            return None

        return TargetRadarModel(
            attacker_index=attacker_index,
            target_index=target_index,
            is_static=self.ctx.phase in TARGET_RADAR_STATIC_PHASES,
        )

    def _build_message_window(self) -> Optional[MessageWindowModel]:
        if self.ctx.phase not in MESSAGE_WINDOW_PHASES:
            return None
        max_lines = BattleTiming.LOG_DISPLAY_MAX
        return MessageWindowModel(
            lines=list(self.ctx.battle_log[-max_lines:]),
            show_advance_marker=self.visual.is_waiting_for_advance(self.ctx.phase),
        )

    def _build_command_menu(self, selected_button_index: int) -> Optional[CommandMenuModel]:
        if self.ctx.phase not in COMMAND_MENU_PHASES or not self.ctx.current_actor:
            return None

        items = build_command_menu_items(self.ctx.current_actor, self.ctx.preview_targets, self.ctx.robots)
        if not items:
            return None

        selected = selected_button_index if 0 <= selected_button_index < len(items) else 0
        selected_item = items[selected]

        preview_indices = []
        if selected_item.preview_target_robot_index is not None:
            preview_indices.append(selected_item.preview_target_robot_index)

        return CommandMenuModel(
            actor_name=self.ctx.current_actor.name,
            selected_index=selected,
            items=items,
            preview_target_robot_indices=preview_indices,
        )

    def _build_cutin(self) -> Optional[CutinModel]:
        director = self.visual.cutin_director
        if self.ctx.phase not in CUTIN_PHASES or director is None:
            return None
        actor = self.ctx.current_actor
        report = self.ctx.current_report
        if not (actor and report and report.target):
            return None

        visual_states = self.visual.visual_states
        actor_model = _build_cutin_actor(actor, visual_states[actor])
        target_model = _build_cutin_actor(report.target, visual_states[report.target])

        return _build_cutin_model(director, actor_model, target_model)

    def _build_overlay(self, phase: BattlePhase) -> Optional[OverlayModel]:
        if phase == BattlePhase.OPENING_POPUP:
            return OverlayModel(opening_popup_visible=True)
        if phase == BattlePhase.GAME_OVER:
            return OverlayModel(game_over_winner=self.ctx.winner)
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