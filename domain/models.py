# domain/models.py
"""ドメインモデルのデータクラス定義"""
import random
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Protocol, Sequence, Tuple, TYPE_CHECKING, Union
from domain.constants import (
    AttributeType, CustomizeSlot, EffectStackPolicy, EffectType, GaugeStatus, HitPolicy,
    PartType, ActionType, PersonalityType, TeamType, SkillType,
)
from domain.effect_payloads import AppliedEffect, PartDamage, PierceDamage, TrapInstall

if TYPE_CHECKING:
    from domain.action_logic import ActionDefinition


class CombatantLeaderProtocol(Protocol):
    """勝敗判定に必要な機体情報の最小プロトコル"""
    team: TeamType
    is_leader: bool
    is_alive: bool


class CombatantTargetProtocol(Protocol):
    """距離ベースのターゲット選定に必要な機体情報の最小プロトコル"""
    team: TeamType
    is_alive: bool
    position: float


class GameDataProtocol(Protocol):
    """GameDataManager の公開インターフェースプロトコル"""
    def get_part_data(self, part_id: str) -> Optional["PartData"]: ...
    def get_medal_data(self, medal_id: str) -> Optional["MedalData"]: ...
    def get_part_name(self, item_id: str) -> str: ...
    def get_part_ids_for_type(self, slot_type: Union[CustomizeSlot, PartType, str]) -> List[str]: ...


class SaveDataProtocol(Protocol):
    """SaveDataManager の公開インターフェースプロトコル"""
    def get_robot_setup(self, robot_idx: int) -> Optional["RobotSetup"]: ...
    def get_part_id(self, robot_idx: int, slot_type: Union[CustomizeSlot, str]) -> str: ...
    def update_part(self, robot_idx: int, slot_type: Union[CustomizeSlot, str], part_id: str) -> None: ...


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
    proficiency: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "MedalData":
        return cls(
            name=data.get("name", ""),
            nickname=data.get("nickname", ""),
            personality=PersonalityType.from_key(data.get("personality")),
            attribute=AttributeType.from_key(data.get("attribute", "")),
            proficiency=data.get("proficiency", {}),
        )


@dataclass(frozen=True)
class PartCombatStats:
    name: str
    medal_attr: AttributeType
    action: Optional[ActionType] = None
    skill: Optional[SkillType] = None
    attribute: AttributeType = AttributeType.UNDEFINED
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
    proficiency_bonus: int = 0
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
            proficiency_bonus=0,
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
    """戦闘行動の判定・計算結果 DTO。

    主攻撃のダメージ量や被弾部位は applied_effects 内の PartDamage オブジェクトから導出されます。
    """
    success: bool
    is_guarded: bool = False
    is_critical: bool = False
    skill: Optional[SkillType] = None
    applied_effects: Tuple[AppliedEffect, ...] = ()
    adjusted_success: int = 0
    adjusted_mobility: int = 0
    target_part: Optional[PartType] = None
    _primary_damage: Optional[PartDamage] = field(init=False, repr=False, default=None)
    _pierce_effect: Optional[PierceDamage] = field(init=False, repr=False, default=None)

    def __post_init__(self):
        if not isinstance(self.applied_effects, tuple):
            object.__setattr__(self, 'applied_effects', tuple(self.applied_effects))
        primary = next((e for e in self.applied_effects if isinstance(e, PartDamage)), None)
        pierce = next((e for e in self.applied_effects if isinstance(e, PierceDamage)), None)
        object.__setattr__(self, '_primary_damage', primary)
        object.__setattr__(self, '_pierce_effect', pierce)

    @property
    def primary_damage(self) -> Optional[PartDamage]:
        return self._primary_damage

    @property
    def damage(self) -> int:
        if self._primary_damage:
            return self._primary_damage.amount
        trap_effect = next((e for e in self.applied_effects if isinstance(e, TrapInstall)), None)
        if trap_effect:
            return trap_effect.trap.damage
        return 0

    @property
    def effective_damage(self) -> int:
        return self._primary_damage.effective_damage if self._primary_damage else 0

    @property
    def hit_part(self) -> Optional[PartType]:
        if self._primary_damage:
            return self._primary_damage.part_type
        return self.target_part

    @property
    def pierce_effect(self) -> Optional[PierceDamage]:
        return self._pierce_effect

    @property
    def has_pierce(self) -> bool:
        return self.success and (self._pierce_effect is not None)


@dataclass(frozen=True)
class TacticsContext:
    hp_map: Dict[PartType, int] = field(default_factory=dict)
    active_effects: Sequence[StatusEffect] = ()