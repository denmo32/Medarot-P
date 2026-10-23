# features/battle/entities/robot.py
"""機体 (Robot) の集約ルートエンティティ定義。"""
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from domain.action_logic import ActionDefinition
from domain.constants import (
    ACTIONABLE_PART_TYPES,
    AttributeType,
    GaugeStatus,
    PartType,
    SkillKind,
    TeamType,
)
from domain.models import (
    BattleParticipant,
    DefensiveInfo,
    MedalData,
    PartCombatStats,
    StatusEffect,
    TargetPartInfo,
)

from .atb_track import ATBEvent, ATBTrack
from .commands import ExecutionOutcome, PartCommand
from .effect_tracker import EffectTracker
from .part import Part

if TYPE_CHECKING:
    from .commands import BattleCommand


class Robot:
    """機体（メダロット）の集約ルート。"""

    def __init__(
        self,
        team: TeamType,
        is_leader: bool,
        name: str,
        medal_data: MedalData,
        parts: Dict[PartType, Part],
    ):
        self.team = team
        self.is_leader = is_leader
        self.name = name
        self.medal_data = medal_data
        self.personality = self.medal_data.personality
        self._parts: Dict[PartType, Part] = parts

        self.atb = ATBTrack()
        self.effects = EffectTracker()
        self.current_command: Optional['BattleCommand'] = None

    # === 基本プロパティ ===
    @property
    def gauge_status(self) -> GaugeStatus: return self.atb.status
    @property
    def position(self) -> float: return self.atb.position
    @property
    def is_charging(self) -> bool: return self.atb.status == GaugeStatus.CHARGING
    @property
    def is_cooling(self) -> bool: return self.atb.status == GaugeStatus.COOLDOWN
    @property
    def head(self) -> Optional[Part]: return self._parts.get(PartType.HEAD)
    @property
    def legs(self) -> Optional[Part]: return self._parts.get(PartType.LEGS)

    @property
    def is_alive(self) -> bool:
        return self.head is not None and self.head.is_alive

    @property
    def current_mobility(self) -> int:
        return self.legs.mobility if self.legs and self.legs.is_alive else 0

    @property
    def current_defense(self) -> int:
        return self.legs.defense if self.legs and self.legs.is_alive else 0

    # === 外部インターフェース・データ取得 ===

    def get_part(self, part_type: PartType) -> Optional[Part]:
        return self._parts.get(part_type)

    def is_part_alive(self, part_type: PartType) -> bool:
        part = self._parts.get(part_type)
        return part is not None and part.is_alive

    def get_part_hp(self, part_type: PartType) -> int:
        part = self._parts.get(part_type)
        return part.hp if part else 0

    def get_parts_hp(self) -> Dict[PartType, int]:
        return {pt: p.hp for pt, p in self._parts.items()}

    def get_parts_max_hp(self) -> Dict[PartType, int]:
        return {pt: p.max_hp for pt, p in self._parts.items()}

    def get_legs_stats(self) -> Dict[str, int]:
        return {"mobility": self.current_mobility, "defense": self.current_defense}

    # === EffectTracker への委譲 ===
    @property
    def is_stopped(self) -> bool:
        return self.effects.is_stopped()

    def is_part_stopped(self, part_type: PartType) -> bool:
        return self.effects.is_part_stopped(part_type)

    @property
    def active_effects(self) -> Tuple[StatusEffect, ...]:
        return tuple(self.effects.active_effects)

    # === パーツコレクションの集約 ===
    @property
    def total_hp(self) -> int:
        return sum(p.hp for p in self._parts.values())

    @property
    def has_broken_parts(self) -> bool:
        return any(p.is_broken for p in self._parts.values())

    def get_target_parts_info(self) -> Dict[PartType, TargetPartInfo]:
        return {
            pt: TargetPartInfo(hp=p.hp, attack=p.attack, mobility=p.mobility)
            for pt, p in self._parts.items()
            if p.is_alive
        }

    @property
    def current_part_command(self) -> Optional[PartCommand]:
        if isinstance(self.current_command, PartCommand):
            return self.current_command
        return None

    @property
    def current_part(self) -> Optional[Part]:
        cmd = self.current_part_command
        return self._parts.get(cmd.part_type) if cmd else None

    # === ライフサイクル（ATB進行とEffect進行を明確に分離） ===

    def tick_atb(self, dt: float) -> Optional[ATBEvent]:
        """ATBゲージ時間を進行させ、端到達イベントを返す"""
        if not self.is_alive:
            return None
        return self.atb.advance(dt, is_paused=self.is_stopped)

    def tick_effects(self, dt: float):
        """充填または放熱中の効果時間を進行させる"""
        if self.is_alive and (self.is_charging or self.is_cooling):
            self.effects.update(dt)

    def set_command(self, command: 'BattleCommand'):
        self.current_command = command
        duration = 1.0
        if isinstance(command, PartCommand):
            part = self._parts.get(command.part_type)
            if part:
                duration = part.calculate_charge_duration()
        self.atb.start_charge(duration)

    def start_execution(self):
        self.effects.clear_stances()
        self.atb.start_execution()

    def finish_execution_to_cooldown(self):
        self.atb.enter_cooldown_from_execution()

    def abort_charging_to_cooldown(self):
        self.atb.abort_charge_to_cooldown()

    def enter_ready(self):
        self.current_command = None
        self.atb.enter_ready()

    # === 自己診断 ===

    def can_execute_part(self, part_type: PartType) -> bool:
        part = self._parts.get(part_type)
        return part.can_execute if part else False

    def get_actionable_part_types(self) -> List[PartType]:
        return [pt for pt in ACTIONABLE_PART_TYPES if self.can_execute_part(pt)]

    def validate_actionable_part(
        self, part_type: PartType
    ) -> Tuple[Optional[Part], ExecutionOutcome]:
        part = self._parts.get(part_type)
        if not part or not part.is_alive:
            return None, ExecutionOutcome.PART_UNUSABLE
        if not part.is_implemented:
            return None, ExecutionOutcome.ACTION_UNIMPLEMENTED
        if self.is_part_stopped(part_type):
            return None, ExecutionOutcome.PART_STOPPED
        return part, ExecutionOutcome.OK

    def is_target_lost(self, target_robot: Optional['Robot'], target_part: Optional[PartType], targets_part: bool) -> bool:
        """指定されたターゲットが喪失（撃沈または指定部位破壊）しているかを判定"""
        if not target_robot or not target_robot.is_alive:
            return True
        if targets_part and target_part:
            if not target_robot.is_part_alive(target_part):
                return True
        return False

    def evaluate_interruption(self) -> Optional[ExecutionOutcome]:
        """充填中の割り込み（予約パーツ破壊または予約ターゲット喪失）を評価"""
        if not self.is_alive or not self.is_charging:
            return None

        cmd = self.current_part_command
        if not cmd:
            return None

        part = self._parts.get(cmd.part_type)
        if not part or not part.is_alive:
            return ExecutionOutcome.RESERVED_PART_DESTROYED

        if part.locks_target:
            if self.is_target_lost(cmd.target_robot, cmd.target_part, part.targets_part):
                return ExecutionOutcome.TARGET_LOST

        return None

    def can_intercept(self, target_robot: 'Robot') -> bool:
        return (
            self.team == target_robot.team
            and self is not target_robot
            and self.is_alive
            and self.effects.is_blocking()
        )

    # === 戦闘スナップショットの生成 ===

    def to_participant(self, active_part: Optional[Part] = None) -> BattleParticipant:
        if active_part:
            stats = active_part.to_combat_stats()
        else:
            stats = PartCombatStats(
                name=self.name,
                action=None,
                skill=None,
                attribute=AttributeType.UNDEFINED,
                medal_attr=self.medal_data.attribute,
            )

        return BattleParticipant(
            stats=stats,
            legs_stats=self.get_legs_stats(),
            parts_hp=self.get_parts_hp(),
            defensive_info=DefensiveInfo(
                gauge_status=self.gauge_status,
                action_def=self._resolve_defensive_action_def(),
            ),
            buff_success=self.effects.get_buff_success(),
            damage_reduction=self.effects.get_protect_reduction(self.is_part_alive),
        )

    def _resolve_defensive_action_def(self) -> Optional[ActionDefinition]:
        part = self.current_part
        return part.action_def if part else None

    # === 状態変更 ===

    def apply_damage(self, part_type: PartType, amount: int) -> Tuple[int, bool]:
        part = self._parts.get(part_type)
        if not part or not part.is_alive:
            return 0, False
        hp_before = part.hp
        is_destroyed = part.take_damage(amount)
        return min(amount, hp_before), is_destroyed

    def apply_repair(
        self, amount: int, specific_part: PartType
    ) -> Optional[Tuple[PartType, int]]:
        part = self._parts.get(specific_part)
        if part and part.is_alive:
            actual = part.repair(amount)
            return (specific_part, actual) if actual > 0 else None
        return None

    def apply_restore(self, specific_part: PartType) -> Optional[PartType]:
        part = self._parts.get(specific_part)
        if part and part.is_broken:
            if part.restore():
                return specific_part
        return None

    def apply_status(self, effect: StatusEffect):
        self.effects.add(effect)

    def on_action_completed(self) -> List[StatusEffect]:
        part = self.current_part
        if part and part.skill_kind == SkillKind.ATTACK:
            return self.effects.consume_attack_charges()
        return []