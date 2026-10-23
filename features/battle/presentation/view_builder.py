"""BattleContext, VisualCoordinator および BattleDirector から表示専用モデルを生成する。"""
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
from features.battle.constants import BattleTiming
from features.battle.staging.cutin_director import CutinDirector, CutinStep
from features.battle.staging.director import BattleDirector
from features.battle.staging.visual_coordinator import VisualCoordinator
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
    director: CutinDirector,
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


class BattleViewBuilder:
    """戦闘状態（Context）、演出状態（Visual）および進行管理（Director）から描画モデルを一括生成する"""

    def __init__(self, ctx: 'BattleContext', visual: VisualCoordinator, director: BattleDirector):
        self.ctx = ctx
        self.visual = visual
        self.director = director

        # 不変なチーム別機体数・グループ分けのキャッシュ（毎フレームの反復ループ抑制）
        self._team_counts = {}
        for robot in ctx.robots:
            self._team_counts[robot.team] = self._team_counts.get(robot.team, 0) + 1

        self._player_robots = [r for r in ctx.robots if r.team == TeamType.PLAYER]
        self._enemy_robots = [r for r in ctx.robots if r.team == TeamType.ENEMY]

    def build(self, selected_button_index: int = 0) -> BattleRenderModel:
        cutin = self._build_cutin()
        command_menu = self._build_command_menu(selected_button_index)
        target_radar = self._build_target_radar()
        message_window = self._build_message_window(command_menu is not None)
        overlay = self._build_overlay()
        top_status = self._build_top_status()

        return BattleRenderModel(
            show_field=True,
            show_message_window=message_window is not None,
            show_command_menu=command_menu is not None,
            show_cutin=cutin is not None,
            show_opening_popup=overlay is not None and overlay.opening_popup_visible,
            show_game_over=overlay is not None and overlay.game_over_winner is not None,
            show_target_radar=target_radar is not None,
            show_preview_target_markers=bool(command_menu and command_menu.preview_target_robot_indices),
            robots=self._build_robots(),
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
                team_count=self._team_counts[robot.team],
            ))
        return views

    def _build_top_status(self) -> TopStatusPanelModel:
        combat_robots = set()

        if self.visual.active_actor is not None and self.visual.active_target is not None:
            combat_robots = {id(self.visual.active_actor), id(self.visual.active_target)}

        return TopStatusPanelModel(
            player_cards=[self._build_robot_card(i, r, id(r) in combat_robots) for i, r in enumerate(self._player_robots)],
            enemy_cards=[self._build_robot_card(i, r, id(r) in combat_robots) for i, r in enumerate(self._enemy_robots)],
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
        command = robot.current_part_command
        if command is None:
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
        radar_dir = self.visual.radar_director
        if radar_dir is None:
            return None

        state = radar_dir.evaluate(is_static=False)
        return TargetRadarModel(
            attacker_index=radar_dir.attacker_index,
            target_index=radar_dir.target_index,
            travel_progress=state.travel_progress,
            scale=state.scale,
            is_static=False,
        )

    def _build_message_window(self, is_command_menu_open: bool) -> Optional[MessageWindowModel]:
        if is_command_menu_open:
            return None

        can_advance = self.director.can_user_confirm and not self.visual.is_hp_animating()
        max_lines = BattleTiming.LOG_DISPLAY_MAX

        return MessageWindowModel(
            lines=list(self.ctx.battle_log[-max_lines:]),
            show_advance_marker=can_advance,
        )

    def _build_command_menu(self, selected_button_index: int) -> Optional[CommandMenuModel]:
        input_await = self.director.current_player_input_await
        if input_await is None:
            return None

        actor = input_await.actor
        items = build_command_menu_items(actor, input_await.preview_targets, self.ctx.robots)
        if not items:
            return None

        selected = selected_button_index if 0 <= selected_button_index < len(items) else 0
        selected_item = items[selected]

        preview_indices = []
        if selected_item.preview_target_robot_index is not None:
            preview_indices.append(selected_item.preview_target_robot_index)

        return CommandMenuModel(
            actor_name=actor.name,
            selected_index=selected,
            items=items,
            preview_target_robot_indices=preview_indices,
        )

    def _build_cutin(self) -> Optional[CutinModel]:
        director = self.visual.cutin_director
        actor = self.visual.active_actor
        target = self.visual.active_target
        if director is None or actor is None or target is None:
            return None

        visual_states = self.visual.visual_states
        actor_model = _build_cutin_actor(actor, visual_states[actor])
        target_model = _build_cutin_actor(target, visual_states[target])

        return _build_cutin_model(director, actor_model, target_model)

    def _build_overlay(self) -> Optional[OverlayModel]:
        if self.director.opening_popup_visible:
            return OverlayModel(opening_popup_visible=True)
        if self.director.is_game_over:
            return OverlayModel(game_over_winner=self.ctx.winner)
        return None


def _build_cutin_actor(robot, visual_state) -> CutinActorModel:
    is_alive = visual_state.is_visually_alive
    return CutinActorModel(
        team=robot.team,
        part_status=dict(visual_state.parts_break_progress),
        accent_state=_resolve_accent_state(robot.gauge_status, is_alive, robot.is_stopped),
    )