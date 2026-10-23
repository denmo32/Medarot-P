# features/battle/presentation/view_builder.py
"""BattleContext, VisualCoordinator および BattleDirector から表示専用モデルを生成する。"""
import dataclasses
from typing import Dict, List, Optional, TYPE_CHECKING
from domain.constants import (
    ALL_PART_TYPES,
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
    from features.battle.entities.robot import Robot

CUTIN_POPUP_LABELS = {
    "critical": "CRITICAL!!",
    "guard": "GUARD",
    "hit": "HIT!",
    "miss": "MISS!",
    "pierce": "PENETRATION",
}


@dataclasses.dataclass(frozen=True)
class _RobotVisualSnapshot:
    """フレーム単位で導出されたロボットの視覚情報キャッシュ"""
    is_alive: bool
    accent_state: AccentState
    part_break_progress: Dict
    parts_display_hp: Dict


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


def _resolve_cutin_popup(result: Optional[ActionResult], step: CutinStep) -> Optional[CutinPopupModel]:
    if result is None:
        return None

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


class BattleViewBuilder:
    """戦闘状態（Context）、演出状態（Visual）および進行管理（Director）から描画モデルを一括生成する"""

    def __init__(self, ctx: 'BattleContext', visual: VisualCoordinator, director: BattleDirector):
        self.ctx = ctx
        self.visual = visual
        self.director = director

        self._player_robots: List['Robot'] = []
        self._enemy_robots: List['Robot'] = []
        for robot in ctx.robots:
            if robot.team == TeamType.PLAYER:
                self._player_robots.append(robot)
            else:
                self._enemy_robots.append(robot)

        self._team_counts = {
            TeamType.PLAYER: len(self._player_robots),
            TeamType.ENEMY: len(self._enemy_robots),
        }

    def _build_snapshot_map(self) -> Dict['Robot', _RobotVisualSnapshot]:
        """全機体の視覚情報を1回だけ導出して辞書化"""
        snapshots = {}
        for robot in self.ctx.robots:
            vs = self.visual.visual_states[robot]
            is_alive = vs.is_visually_alive
            accent = _resolve_accent_state(robot.gauge_status, is_alive, robot.is_stopped)
            snapshots[robot] = _RobotVisualSnapshot(
                is_alive=is_alive,
                accent_state=accent,
                part_break_progress=dict(vs.parts_break_progress),
                parts_display_hp=dict(vs.parts_display_hp),
            )
        return snapshots

    def build(self, selected_button_index: int = 0) -> BattleRenderModel:
        snapshots = self._build_snapshot_map()

        cutin = self._build_cutin(snapshots)
        command_menu = self._build_command_menu(selected_button_index)
        target_radar = self._build_target_radar()
        message_window = self._build_message_window(command_menu is not None)
        overlay = self._build_overlay()
        top_status = self._build_top_status(snapshots)

        return BattleRenderModel(
            show_field=True,
            show_message_window=message_window is not None,
            show_command_menu=command_menu is not None,
            show_cutin=cutin is not None,
            show_opening_popup=overlay is not None and overlay.opening_popup_visible,
            show_game_over=overlay is not None and overlay.game_over_winner is not None,
            show_target_radar=target_radar is not None,
            show_preview_target_markers=bool(command_menu and command_menu.preview_target_robot_indices),
            robots=self._build_robots(snapshots),
            target_radar=target_radar,
            message_window=message_window,
            command_menu=command_menu,
            cutin=cutin,
            overlay=overlay,
            top_status=top_status,
        )

    def _build_robots(self, snapshots: Dict['Robot', _RobotVisualSnapshot]) -> List[RobotViewModel]:
        team_indexes = {}
        views: List[RobotViewModel] = []

        for index, robot in enumerate(self.ctx.robots):
            team_index = team_indexes.get(robot.team, 0)
            team_indexes[robot.team] = team_index + 1
            snap = snapshots[robot]

            views.append(RobotViewModel(
                index=index,
                team=robot.team,
                is_alive=snap.is_alive,
                gauge_status=robot.gauge_status,
                is_stopped=robot.is_stopped,
                accent_state=snap.accent_state,
                part_status=snap.part_break_progress,
                part_stopped={pt: robot.is_part_stopped(pt) for pt in ALL_PART_TYPES},
                progress_ratio=robot.position,
                team_index=team_index,
                team_count=self._team_counts[robot.team],
            ))
        return views

    def _build_top_status(self, snapshots: Dict['Robot', _RobotVisualSnapshot]) -> TopStatusPanelModel:
        return TopStatusPanelModel(
            player_cards=[
                self._build_robot_card(i, r, snapshots[r], self.visual.is_combat_active(r))
                for i, r in enumerate(self._player_robots)
            ],
            enemy_cards=[
                self._build_robot_card(i, r, snapshots[r], self.visual.is_combat_active(r))
                for i, r in enumerate(self._enemy_robots)
            ],
        )

    def _build_robot_card(
        self, robot_index: int, robot: 'Robot', snap: _RobotVisualSnapshot, is_combat_active: bool = False
    ) -> RobotStatusCardModel:
        parts_hp: List[PartMiniHpModel] = []

        for part_type in ALL_PART_TYPES:
            part = robot.get_part(part_type)
            if not part:
                continue
            display_hp = float(snap.parts_display_hp.get(part_type, part.hp))
            max_hp = max(1, part.max_hp)
            parts_hp.append(PartMiniHpModel(
                part_type=part_type,
                label=part_type.label,
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
            is_alive=snap.is_alive,
            accent_state=snap.accent_state,
            target_text=self._build_target_text(robot),
            badges=self._build_effect_badges(robot),
            parts_hp=parts_hp,
            is_combat_active=is_combat_active,
        )

    def _build_target_text(self, robot: 'Robot') -> Optional[str]:
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
                target_label += f" [{command.target_part.label}]"
            return f"└> {target_label}"

        if not part.locks_target:
            return "└> 直前選定"
        return None

    def _build_effect_badges(self, robot: 'Robot') -> List[EffectBadgeModel]:
        badges: List[EffectBadgeModel] = []
        for effect in robot.active_effects:
            if effect.type == EffectType.STOP:
                text = "停止"
                if effect.part_type:
                    text += f" {effect.part_type.label}"
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
        items = input_await.items
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

    def _build_cutin(self, snapshots: Dict['Robot', _RobotVisualSnapshot]) -> Optional[CutinModel]:
        director = self.visual.cutin_director
        if director is None:
            return None

        actor_snap = snapshots[director.actor]
        target_snap = snapshots[director.target]

        actor_model = CutinActorModel(
            team=director.actor.team,
            part_status=actor_snap.part_break_progress,
            accent_state=actor_snap.accent_state,
        )
        target_model = CutinActorModel(
            team=director.target.team,
            part_status=target_snap.part_break_progress,
            accent_state=target_snap.accent_state,
        )

        return self._build_cutin_timeline(director, actor_model, target_model)

    def _build_cutin_timeline(
        self,
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

        is_hit = result.success if result else False

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

    def _build_overlay(self) -> Optional[OverlayModel]:
        if self.director.opening_popup_visible:
            return OverlayModel(opening_popup_visible=True)
        if self.director.is_game_over:
            return OverlayModel(game_over_winner=self.ctx.winner)
        return None