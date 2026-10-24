"""バトル画面の表示専用データ構造（UIへの逆依存を排除した純粋DTO）。"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from domain.constants import (
    AccentState,
    PartType,
    TeamType,
)
from features.battle.staging.cutin_timeline import (
    ActorMotion as ActorMotionModel,
    ImpactMotion as ImpactEffectModel,
    ProjectileMotion as ProjectileEffectModel,
)

if TYPE_CHECKING:
    from features.battle.simulation.entities.robot import Robot
    from features.battle.staging.visual_state import RobotVisualState


@dataclass(frozen=True)
class RobotRenderContext:
    """機体ごとの描画に必要なエンティティと視覚状態の最小限の束ねオブジェクト"""
    index: int
    robot: 'Robot'
    visual_state: 'RobotVisualState'
    team_index: int
    team_count: int
    accent_state: AccentState
    is_combat_active: bool = False

    @property
    def team(self) -> TeamType:
        return self.robot.team

    @property
    def progress_ratio(self) -> float:
        return self.robot.position


@dataclass(frozen=True)
class CommandMenuItemModel:
    """コマンドメニュー項目の表示用モデル（part_type=None はスキップを表す）"""
    part_type: Optional[PartType]
    label: str
    action_label: str
    visual_enabled: bool
    selectable: bool
    preview_target_robot_index: Optional[int] = None


@dataclass(frozen=True)
class CommandMenuModel:
    actor_name: str
    selected_index: int
    items: List[CommandMenuItemModel]
    preview_target_robot_indices: List[int] = field(default_factory=list)


@dataclass(frozen=True)
class MessageWindowModel:
    lines: List[str]
    show_advance_marker: bool


@dataclass(frozen=True)
class TargetRadarModel:
    attacker_index: int
    target_index: int
    travel_progress: float = 1.0
    scale: float = 1.0


@dataclass(frozen=True)
class CutinActorModel:
    team: TeamType
    part_status: Dict[PartType, float]
    accent_state: AccentState
    is_visible: bool = True
    motion: Optional[ActorMotionModel] = None


@dataclass(frozen=True)
class CutinPopupModel:
    primary_label: str
    damage_label: str
    is_miss: bool


@dataclass(frozen=True)
class CutinModel:
    actor: CutinActorModel
    target: CutinActorModel
    popup: Optional[CutinPopupModel] = None
    projectiles: List[ProjectileEffectModel] = field(default_factory=list)
    impacts: List[ImpactEffectModel] = field(default_factory=list)
    camera_progress: Optional[float] = None


@dataclass(frozen=True)
class BattleRenderModel:
    """1フレームの描画に必要な全情報（冗長フラグを廃止）"""
    robots: List[RobotRenderContext]
    player_robots: List[RobotRenderContext]
    enemy_robots: List[RobotRenderContext]
    command_menu: Optional[CommandMenuModel] = None
    message_window: Optional[MessageWindowModel] = None
    cutin: Optional[CutinModel] = None
    target_radar: Optional[TargetRadarModel] = None
    opening_popup_visible: bool = False
    game_over_winner: Optional[TeamType] = None