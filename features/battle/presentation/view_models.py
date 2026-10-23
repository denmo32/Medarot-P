"""バトル画面の表示専用データ構造（UIへの逆依存を排除した純粋DTO）。"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from domain.constants import (
    AccentState,
    BadgeKind,
    CommandSlot,
    GaugeStatus,
    PartType,
    TeamType,
)
from features.battle.constants import BattlePhase
from features.battle.staging.cutin_timeline import (
    ActorMotion as ActorMotionModel,
    ImpactMotion as ImpactEffectModel,
    ProjectileMotion as ProjectileEffectModel,
)


@dataclass(frozen=True)
class CommandMenuItemModel:
    """コマンドメニュー項目の表示用モデル"""
    slot_type: CommandSlot
    label: str
    action_label: str
    visual_enabled: bool
    selectable: bool
    preview_target_robot_index: Optional[int] = None


@dataclass(frozen=True)
class RobotViewModel:
    index: int
    team: TeamType
    is_alive: bool
    gauge_status: GaugeStatus
    is_stopped: bool
    accent_state: AccentState
    part_status: Dict[PartType, float]
    part_stopped: Dict[PartType, bool]
    progress_ratio: float
    team_index: int
    team_count: int


@dataclass(frozen=True)
class TargetRadarModel:
    attacker_index: int
    target_index: int
    travel_progress: float = 1.0  # 0.0 (攻撃側) 〜 1.0 (対象側)
    scale: float = 1.0            # 拡縮倍率
    is_static: bool = False


@dataclass(frozen=True)
class MessageWindowModel:
    lines: List[str]
    show_advance_marker: bool


@dataclass(frozen=True)
class CommandMenuModel:
    actor_name: str
    selected_index: int
    items: List[CommandMenuItemModel]
    preview_target_robot_indices: List[int] = field(default_factory=list)


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
class OverlayModel:
    opening_popup_visible: bool = False
    game_over_winner: Optional[TeamType] = None


@dataclass(frozen=True)
class PartMiniHpModel:
    part_type: PartType
    label: str
    current_hp: int
    max_hp: int
    ratio: float
    is_broken: bool
    is_stopped: bool


@dataclass(frozen=True)
class EffectBadgeModel:
    text: str
    badge_kind: BadgeKind


@dataclass(frozen=True)
class RobotStatusCardModel:
    robot_index: int
    name: str
    team: TeamType
    is_leader: bool
    is_alive: bool
    accent_state: AccentState
    target_text: Optional[str]
    badges: List[EffectBadgeModel]
    parts_hp: List[PartMiniHpModel]
    is_combat_active: bool = False


@dataclass(frozen=True)
class TopStatusPanelModel:
    player_cards: List[RobotStatusCardModel]
    enemy_cards: List[RobotStatusCardModel]


@dataclass(frozen=True)
class BattleRenderModel:
    show_field: bool
    show_message_window: bool
    show_command_menu: bool
    show_cutin: bool
    show_opening_popup: bool
    show_game_over: bool
    show_target_radar: bool
    show_preview_target_markers: bool
    robots: List[RobotViewModel]
    target_radar: Optional[TargetRadarModel] = None
    message_window: Optional[MessageWindowModel] = None
    command_menu: Optional[CommandMenuModel] = None
    cutin: Optional[CutinModel] = None
    overlay: Optional[OverlayModel] = None
    top_status: Optional[TopStatusPanelModel] = None