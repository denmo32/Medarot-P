"""BattleManager および BattleDirector から表示モデルを効率的に生成する。"""
import dataclasses
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from domain.constants import (
    AccentState,
    GaugeStatus,
    TeamType,
)
from domain.models import ActionResult
from features.battle.constants import BattleTiming
from features.battle.staging.cutin_director import CutinDirector, CutinStep
from features.battle.staging.director import BattleDirector
from .view_models import (
    BattleRenderModel,
    CommandMenuModel,
    CutinActorModel,
    CutinModel,
    CutinPopupModel,
    MessageWindowModel,
    RobotRenderContext,
    TargetRadarModel,
)

if TYPE_CHECKING:
    from features.battle.simulation.manager import BattleManager
    from features.battle.simulation.entities.robot import Robot

CUTIN_POPUP_LABELS = {
    "critical": "CRITICAL!!",
    "guard": "GUARD",
    "hit": "HIT!",
    "miss": "MISS!",
    "pierce": "PENETRATION",
}


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
    """戦闘状態（Manager）および進行管理（Director）から描画モデルを一括生成する"""

    def __init__(self, manager: 'BattleManager', director: BattleDirector):
        self.manager = manager
        self.director = director

        self._team_counts = {
            TeamType.PLAYER: sum(1 for r in manager.robots if r.team == TeamType.PLAYER),
            TeamType.ENEMY: sum(1 for r in manager.robots if r.team == TeamType.ENEMY),
        }

    def build(self, selected_button_index: int = 0) -> BattleRenderModel:
        # 各ロボットの軽量コンテキスト生成
        all_robots: List[RobotRenderContext] = []
        player_robots: List[RobotRenderContext] = []
        enemy_robots: List[RobotRenderContext] = []

        team_indices = {TeamType.PLAYER: 0, TeamType.ENEMY: 0}

        for idx, robot in enumerate(self.manager.robots):
            t_idx = team_indices[robot.team]
            team_indices[robot.team] += 1

            vs = self.director.visual_states[robot]
            accent = _resolve_accent_state(robot.gauge_status, vs.is_visually_alive, robot.is_stopped)

            ctx = RobotRenderContext(
                index=idx,
                robot=robot,
                visual_state=vs,
                team_index=t_idx,
                team_count=self._team_counts[robot.team],
                accent_state=accent,
                is_combat_active=self.director.is_combat_active(robot),
            )
            all_robots.append(ctx)
            if robot.team == TeamType.PLAYER:
                player_robots.append(ctx)
            else:
                enemy_robots.append(ctx)

        command_menu = self._build_command_menu(selected_button_index)
        message_window = self._build_message_window(command_menu is not None)
        cutin = self._build_cutin()
        target_radar = self._build_target_radar()

        return BattleRenderModel(
            robots=all_robots,
            player_robots=player_robots,
            enemy_robots=enemy_robots,
            command_menu=command_menu,
            message_window=message_window,
            cutin=cutin,
            target_radar=target_radar,
            opening_popup_visible=self.director.opening_popup_visible,
            game_over_winner=self.manager.winner if self.director.is_game_over else None,
        )

    def _build_command_menu(self, selected_button_index: int) -> Optional[CommandMenuModel]:
        input_await = self.director.current_player_input_await
        if input_await is None or not input_await.menu_items:
            return None

        selected = selected_button_index if 0 <= selected_button_index < len(input_await.menu_items) else 0
        selected_item = input_await.menu_items[selected]

        preview_indices = []
        if selected_item.preview_target_robot_index is not None:
            preview_indices.append(selected_item.preview_target_robot_index)

        return CommandMenuModel(
            actor_name=input_await.actor.name,
            selected_index=selected,
            items=input_await.menu_items,
            preview_target_robot_indices=preview_indices,
        )

    def _build_message_window(self, is_command_menu_open: bool) -> Optional[MessageWindowModel]:
        if is_command_menu_open:
            return None

        can_advance = self.director.can_user_confirm and not self.director.is_hp_animating()
        max_lines = BattleTiming.LOG_DISPLAY_MAX

        return MessageWindowModel(
            lines=list(self.director.active_messages[-max_lines:]),
            show_advance_marker=can_advance,
        )

    def _build_target_radar(self) -> Optional[TargetRadarModel]:
        radar_dir = self.director.radar
        if radar_dir is None:
            return None

        state = radar_dir.evaluate(is_static=False)
        return TargetRadarModel(
            attacker_index=radar_dir.attacker_index,
            target_index=radar_dir.target_index,
            travel_progress=state.travel_progress,
            scale=state.scale,
        )

    def _build_cutin(self) -> Optional[CutinModel]:
        director = self.director.cutin
        if director is None:
            return None

        actor_vs = self.director.visual_states[director.actor]
        target_vs = self.director.visual_states[director.target]

        actor_accent = _resolve_accent_state(
            director.actor.gauge_status, actor_vs.is_visually_alive, director.actor.is_stopped
        )
        target_accent = _resolve_accent_state(
            director.target.gauge_status, target_vs.is_visually_alive, director.target.is_stopped
        )

        actor_model = CutinActorModel(
            team=director.actor.team,
            part_status=actor_vs.parts_break_progress,
            accent_state=actor_accent,
        )
        target_model = CutinActorModel(
            team=director.target.team,
            part_status=target_vs.parts_break_progress,
            accent_state=target_accent,
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