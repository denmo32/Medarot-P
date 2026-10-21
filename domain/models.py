"""ドメインモデルのデータクラス定義"""
import random
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Protocol, Sequence, Tuple, TYPE_CHECKING, Union
from domain.config import DEFAULT_APTITUDE_LEVEL
from domain.constants import (
    ActionCategory,
    AttributeType, CustomizeSlot, EffectStackPolicy, EffectType, GaugeStatus, HitPolicy,
    PartType, ActionType, PersonalityType, TeamType, SkillType,
)
from domain.effect_payloads import AppliedEffect, PierceDamage

if TYPE_CHECKING:
    from domain.action_logic import ActionDefinition


class GameDataProtocol(Protocol):
    """GameDataManager の公開インターフェースプロトコル"""
    def get_part_data(self, part_id: str) -> Optional["PartData"]: ...
    def get_medal_data(self, medal_id: str) -> Optional["MedalData"]: ...
    def get_part_name(self, item_id: str) -> str: ...
    def get_part_ids_for_type(self, slot_type: Union[CustomizeSlot, PartType, str]) -> List[str]: ...


@dataclass(frozen=True)
class CategoryProgress:
    """単一カテゴリの成長状態（不変DTO）"""
    value: int = 0
    exp: int = 0


class SaveDataProtocol(Protocol):
    """SaveDataManager の公開インターフェースプロトコル"""
    def get_robot_setup(self, robot_idx: int) -> Optional["RobotSetup"]: ...
    def get_part_id(self, robot_idx: int, slot_type: CustomizeSlot) -> str: ...
    def update_part(self, robot_idx: int, slot_type: CustomizeSlot, part_id: str) -> None: ...
    def get_medal_mastery(self, medal_id: str, category: ActionCategory) -> int: ...
    def get_medal_progress(self, medal_id: str, category: ActionCategory) -> CategoryProgress: ...
    def batch_add_medal_exp(self, updates: Sequence[Tuple[str, ActionCategory, int]]) -> None: ...


@dataclass(frozen=True)
class RobotSetup:
    """機体の編成情報（不変データモデル）"""
    name: str
    medal_id: str
    part_ids: Mapping[PartType, str]

    def get_part_id(self, slot: CustomizeSlot) -> str:
        if slot.is_medal:
            return self.medal_id
        if slot.part_type:
            return self.part_ids.get(slot.part_type, "")
        return ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "medal": self.medal_id,
            "parts": {pt.value: pid for pt, pid in self.part_ids.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RobotSetup":
        parts_raw = data.get("parts", {})
        part_ids = {}
        for raw_k, pid in parts_raw.items():
            pt = PartType.from_key(raw_k)
            if pt:
                part_ids[pt] = pid
        return cls(
            name=data.get("name", "Medarot"),
            medal_id=data.get("medal", ""),
            part_ids=part_ids,
        )


@dataclass(frozen=True)
class TargetPartInfo:
    hp: int
    attack: int = 0
    mobility: int = 0

    @property
    def is_alive(self) -> bool:
        return self.hp > 0


@dataclass(frozen=True)
class PartData:
    name: str
    action: Optional[ActionType]
    skill: Optional[SkillType]
    hp: int
    attack: Optional[int]
    success: int
    mobility: int = 0
    defense: int = 0
    attribute: AttributeType = AttributeType.UNDEFINED

    @classmethod
    def from_dict(cls, data: dict) -> "PartData":
        return cls(
            name=data.get("name", ""),
            action=ActionType.from_key(data.get("action")),
            skill=SkillType.from_key(data.get("skill")),
            hp=data.get("hp", 0),
            attack=data.get("attack"),
            success=data.get("success", 0),
            mobility=data.get("mobility", 0),
            defense=data.get("defense", 0),
            attribute=AttributeType.from_key(data.get("attribute", "")),
        )


@dataclass(frozen=True)
class MedalData:
    name: str
    nickname: str
    personality: PersonalityType = PersonalityType.RANDOM
    attribute: AttributeType = AttributeType.UNDEFINED
    aptitudes: Dict[ActionCategory, int] = field(default_factory=dict)

    def get_aptitude(self, category: Optional[ActionCategory]) -> int:
        if category is None:
            return DEFAULT_APTITUDE_LEVEL
        return self.aptitudes.get(category, DEFAULT_APTITUDE_LEVEL)

    @classmethod
    def from_dict(cls, data: dict) -> "MedalData":
        raw_aptitudes = data.get("aptitude", {})
        aptitudes: Dict[ActionCategory, int] = {}
        for cat in ActionCategory:
            if cat.value in raw_aptitudes:
                aptitudes[cat] = int(raw_aptitudes[cat.value])
            else:
                aptitudes[cat] = DEFAULT_APTITUDE_LEVEL

        return cls(
            name=data.get("name", ""),
            nickname=data.get("nickname", ""),
            personality=PersonalityType.from_key(data.get("personality")),
            attribute=AttributeType.from_key(data.get("attribute", "")),
            aptitudes=aptitudes,
        )


@dataclass(frozen=True)
class PartCombatStats:
    name: str
    action: Optional[ActionType]
    skill: Optional[SkillType]
    attribute: AttributeType
    medal_attr: AttributeType
    hp: int = 0
    attack: int = 0
    base_attack: int = 0
    success: int = 0
    mobility: int = 0
    defense: int = 0
    time_modifier: float = 1.0
    hit_policy: HitPolicy = HitPolicy.STANDARD
    can_pierce: bool = False


@dataclass(frozen=True)
class DefensiveInfo:
    gauge_status: GaugeStatus
    action_def: Optional["ActionDefinition"] = None


@dataclass(frozen=True)
class BattleParticipant:
    stats: PartCombatStats
    legs_stats: Dict[str, int]
    parts_hp: Dict[PartType, int]
    defensive_info: DefensiveInfo
    buff_success: int = 0
    damage_reduction: int = 0


@dataclass(frozen=True)
class EffectResolutionContext:
    attacker_attack: int
    attacker_success: int
    target_mobility: int
    skill: Optional[SkillType] = None
    target_parts_hp: Dict[PartType, int] = field(default_factory=dict)
    target_parts_max_hp: Dict[PartType, int] = field(default_factory=dict)
    target_part_type: Optional[PartType] = None
    source_part_type: Optional[PartType] = None
    rng: random.Random = field(default_factory=random.Random)

    @classmethod
    def from_participants(
        cls,
        attacker: BattleParticipant,
        target: BattleParticipant,
        source_part_type: Optional[PartType],
        target_part_type: Optional[PartType],
        target_parts_max_hp: Dict[PartType, int],
        rng: Optional[random.Random] = None,
    ) -> "EffectResolutionContext":
        return cls(
            attacker_attack=attacker.stats.attack,
            attacker_success=attacker.stats.success + attacker.buff_success,
            target_mobility=target.legs_stats.get("mobility", 0),
            skill=attacker.stats.skill,
            target_parts_hp=target.parts_hp,
            target_parts_max_hp=target_parts_max_hp,
            target_part_type=target_part_type,
            source_part_type=source_part_type,
            rng=rng or random.Random(),
        )


@dataclass(frozen=True)
class StatusEffect:
    type: EffectType
    duration: float
    magnitude: int = 0
    charges: Optional[int] = None
    source: Optional[str] = None
    stack_policy: EffectStackPolicy = EffectStackPolicy.REFRESH_MAX
    part_type: Optional[PartType] = None


@dataclass(frozen=True)
class ActionResult:
    success: bool
    damage: int = 0
    effective_damage: int = 0
    hit_part: Optional[PartType] = None
    is_guarded: bool = False
    is_critical: bool = False
    skill: Optional[SkillType] = None
    applied_effects: List[AppliedEffect] = field(default_factory=list)
    adjusted_success: int = 0
    adjusted_mobility: int = 0

    @property
    def pierce_effect(self) -> Optional[PierceDamage]:
        return next((e for e in self.applied_effects if isinstance(e, PierceDamage)), None)

    @property
    def has_pierce(self) -> bool:
        return self.success and (self.pierce_effect is not None)


@dataclass(frozen=True)
class RobotSnapshot:
    index: int
    team: TeamType
    is_alive: bool
    gauge_status: GaugeStatus
    progress: float
    is_leader: bool = False


@dataclass(frozen=True)
class TacticsContext:
    hp_map: Dict[PartType, int] = field(default_factory=dict)
    active_effects: Sequence[StatusEffect] = ()