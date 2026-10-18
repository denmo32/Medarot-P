"""機体 (Robot) とパーツ (Part) の自律エンティティ定義。"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Iterable, List, Optional, Tuple, TYPE_CHECKING

from domain.action_logic import ActionDefinition, get_action_definition
from domain.attribute import get_passive_bonuses
from domain.constants import (
    ActionType,
    AttributeType,
    GaugeStatus,
    HitPolicy,
    PartType,
    SkillKind,
    SkillPresentation,
    SkillType,
    TargetRule,
    TargetTiming,
    TeamType,
)
from domain.gauge_utils import calculate_base_time
from domain.models import (
    ActionResult,
    BattleParticipant,
    DefensiveInfo,
    EffectResolutionContext,
    MedalData,
    PartCombatStats,
    PartData,
    RobotSnapshot,
    StatusEffect,
    TargetPartInfo,
)

from domain.skills import SkillDefinition, get_skill_definition
from domain.traps import InstalledTrap, TrapManager

from .commands import PartCommand
from .constants import ExecutionOutcome
from .effect_tracker import EffectTracker

if TYPE_CHECKING:
    from .commands import BattleCommand


class ATBEvent(Enum):
    """ATBの端到達イベント"""
    CHARGED = auto()
    COOLED = auto()


@dataclass
class ATBTrack:
    """単一機体のゲージ進行を追跡する純粋データクラス"""
    position: float = 0.0
    status: GaugeStatus = GaugeStatus.READY
    charge_duration: float = 1.0
    cooldown_duration: float = 1.0

    def start_charge(self, duration: float):
        self.charge_duration = max(0.001, duration)
        self.cooldown_duration = max(0.001, duration)
        self.status = GaugeStatus.CHARGING
        self.position = 0.0

    def start_execution(self):
        self.status = GaugeStatus.EXECUTING
        self.position = 1.0

    def enter_cooldown(self, interrupted: bool = False):
        self.status = GaugeStatus.COOLDOWN
        if not interrupted:
            self.position = 1.0

    def enter_ready(self):
        self.status = GaugeStatus.READY
        self.position = 0.0

    def advance(self, dt: float, is_paused: bool = False) -> Optional[ATBEvent]:
        if is_paused:
            return None

        if self.status == GaugeStatus.CHARGING:
            self.position += dt / self.charge_duration
            if self.position >= 1.0:
                self.position = 1.0
                return ATBEvent.CHARGED

        elif self.status == GaugeStatus.COOLDOWN:
            self.position -= dt / self.cooldown_duration
            if self.position <= 0.0:
                self.position = 0.0
                return ATBEvent.COOLED

        return None


class Part:
    """パーツ個別の性能計算、状態管理、HP変動を自律して担うエンティティ"""

    def __init__(self, part_type: PartType, data: PartData, medal_data: MedalData):
        self.part_type = part_type
        self.data = data
        self.medal_data = medal_data
        self.action_def: ActionDefinition = get_action_definition(data.action)
        self.skill_def: SkillDefinition = get_skill_definition(data.skill)

        # メダル属性との一致パッシブボーナスを算出
        self.bonuses = get_passive_bonuses(part_type, data.attribute, medal_data.attribute)

        # 基礎ステータス＋ボーナス
        self.base_attack: int = data.attack or 0
        self.max_hp: int = data.hp + self.bonuses.hp_add
        self.hp: int = self.max_hp

    # === プロパティ ===
    @property
    def name(self) -> str: return self.data.name
    @property
    def action(self) -> Optional[ActionType]: return self.data.action
    @property
    def skill(self) -> Optional[SkillType]: return self.data.skill
    @property
    def attribute(self) -> AttributeType: return self.data.attribute
    @property
    def attack(self) -> int: return self.base_attack + self.bonuses.attack_add
    @property
    def success(self) -> int: return self.data.success + self.bonuses.success_add
    @property
    def mobility(self) -> int: return self.data.mobility + self.bonuses.mobility_add
    @property
    def defense(self) -> int: return self.data.defense + self.bonuses.defense_add
    @property
    def time_modifier(self) -> float:
        return self.action_def.time_modifier * self.bonuses.time_modifier

    @property
    def hit_policy(self) -> HitPolicy: return self.skill_def.hit_policy
    @property
    def can_pierce(self) -> bool: return self.skill_def.can_pierce
    @property
    def skill_kind(self) -> SkillKind: return self.skill_def.skill_kind
    @property
    def presentation(self) -> SkillPresentation: return self.skill_def.presentation
    @property
    def targets_part(self) -> bool: return self.skill_def.targets_part

    @property
    def is_alive(self) -> bool: return self.hp > 0
    @property
    def is_broken(self) -> bool: return self.hp <= 0

    @property
    def is_implemented(self) -> bool:
        return self.action_def.is_implemented and self.skill_def.is_implemented

    @property
    def can_execute(self) -> bool:
        return self.is_alive and self.is_implemented

    @property
    def target_timing(self) -> TargetTiming:
        if self.action_def.fixed_target_timing is not None:
            return self.action_def.fixed_target_timing
        if self.skill_def.target_timing is not None:
            return self.skill_def.target_timing
        return TargetTiming.NONE

    @property
    def target_rule(self) -> TargetRule:
        if self.action_def.fixed_target_rule is not None:
            return self.action_def.fixed_target_rule
        if self.skill_def.target_rule is not None:
            return self.skill_def.target_rule
        return TargetRule.SELF

    @property
    def locks_target(self) -> bool:
        return self.target_timing is TargetTiming.ON_CHARGE

    def calculate_charge_duration(self) -> float:
        """自身の攻撃力と時間補正から充填・放熱所要秒数を計算"""
        base_t = calculate_base_time(self.base_attack)
        return max(0.001, base_t * self.time_modifier)

    def to_combat_stats(self) -> PartCombatStats:
        """現在のパーツとメダルから計算層へ渡す戦闘ステータス集約を生成する"""
        return PartCombatStats(
            name=self.name,
            action=self.action,
            skill=self.skill,
            attribute=self.attribute,
            medal_attr=self.medal_data.attribute,
            hp=self.max_hp,
            attack=self.attack,
            base_attack=self.base_attack,
            success=self.success,
            mobility=self.mobility,
            defense=self.defense,
            time_modifier=self.time_modifier,
            hit_policy=self.hit_policy,
            can_pierce=self.can_pierce,
        )

    def resolve_effect(self, context: EffectResolutionContext) -> ActionResult:
        """技の効果を解決する（SkillDefinition への委譲）"""
        return self.skill_def.resolve_effect(context)

    # === HP操作（自律的な状態変更） ===

    def take_damage(self, amount: int) -> bool:
        """ダメージを受け、この攻撃で破壊されたかを返す"""
        if not self.is_alive:
            return False
        self.hp = max(0, self.hp - amount)
        return self.hp == 0

    def repair(self, amount: int) -> int:
        """パーツのHPを回復し、実際の回復量を返す"""
        if not self.is_alive:
            return 0
        actual = min(amount, self.max_hp - self.hp)
        self.hp += actual
        return actual

    def restore(self, initial_hp: int = 1) -> bool:
        """破壊されたパーツを復活させる"""
        if self.is_alive:
            return False
        self.hp = max(1, min(initial_hp, self.max_hp))
        return True


class Robot:
    """機体（メダロット）の集約ルート。

    配下のパーツ・状態異常・ATBゲージの整合性を完全にカプセル化し、
    外部に生データを晒さず「振る舞い」を通じて状態を変化させる。
    """

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
    def head(self) -> Optional[Part]: return self._parts.get(PartType.HEAD)
    @property
    def legs(self) -> Optional[Part]: return self._parts.get(PartType.LEGS)

    @property
    def is_alive(self) -> bool:
        """頭部パーツが存在し、生存しているか"""
        return self.head is not None and self.head.is_alive

    @property
    def current_mobility(self) -> int:
        return self.legs.mobility if self.legs and self.legs.is_alive else 0

    @property
    def current_defense(self) -> int:
        return self.legs.defense if self.legs and self.legs.is_alive else 0

    # === 外部インターフェース・データ取得（カプセル化） ===

    def get_part(self, part_type: PartType) -> Optional[Part]:
        """指定部位のパーツを取得する（存在しない場合は None）"""
        return self._parts.get(part_type)

    def iter_parts(self) -> Iterable[Tuple[PartType, Part]]:
        """全部位のイテレータを返す"""
        return self._parts.items()

    def is_part_alive(self, part_type: PartType) -> bool:
        """指定部位が存在し生存しているか"""
        part = self._parts.get(part_type)
        return part is not None and part.is_alive

    def get_part_hp(self, part_type: PartType) -> int:
        """指定部位の現在HPを取得する（存在しない場合は0）"""
        part = self._parts.get(part_type)
        return part.hp if part else 0

    def get_parts_hp(self) -> Dict[PartType, int]:
        return {pt: p.hp for pt, p in self._parts.items()}

    def get_parts_max_hp(self) -> Dict[PartType, int]:
        return {pt: p.max_hp for pt, p in self._parts.items()}

    def get_legs_stats(self) -> Dict[str, int]:
        return {"mobility": self.current_mobility, "defense": self.current_defense}

    # === LoD 対策: EffectTracker への委譲 ===
    @property
    def is_stopped(self) -> bool:
        """機体全体（脚部または全体停止）が停止状態にあるか"""
        return self.effects.is_stopped()

    def is_part_stopped(self, part_type: PartType) -> bool:
        """指定部位が停止状態にあるか"""
        return self.effects.is_part_stopped(part_type)

    @property
    def active_effects(self) -> Tuple[StatusEffect, ...]:
        """適用中の状態異常・バフ一覧（防御的コピー）"""
        return tuple(self.effects.active_effects)

    # === LoD 対策: パーツコレクションの集約・情報隠蔽 ===
    @property
    def total_hp(self) -> int:
        """機体の総残りHP"""
        return sum(p.hp for p in self._parts.values())

    @property
    def has_broken_parts(self) -> bool:
        """破壊されたパーツが1つでもあるか"""
        return any(p.is_broken for p in self._parts.values())

    def get_target_parts_info(self) -> Dict[PartType, TargetPartInfo]:
        """ターゲット選定（性格AI）に必要な生存部位の情報を集約して返す"""
        return {
            pt: TargetPartInfo(hp=p.hp, attack=p.attack or 0, mobility=p.mobility)
            for pt, p in self._parts.items()
            if p.is_alive
        }

    @property
    def current_part_command(self) -> Optional[PartCommand]:
        """現在予約されているコマンドがPartCommandであれば返す"""
        if isinstance(self.current_command, PartCommand):
            return self.current_command
        return None

    @property
    def current_part(self) -> Optional[Part]:
        """現在予約されているコマンドの実行対象パーツを取得"""
        cmd = self.current_part_command
        return self._parts.get(cmd.part_type) if cmd else None

    def get_snapshot(self, index: int) -> RobotSnapshot:
        return RobotSnapshot(
            index=index,
            team=self.team,
            is_alive=self.is_alive,
            gauge_status=self.gauge_status,
            progress=self.position,
            is_leader=self.is_leader,
        )

    # === ATB ライフサイクル (自律更新) ===

    def tick(self, dt: float) -> Optional[ATBEvent]:
        """【Hollywood Principle】1フレーム分の時間を自律進行させ、端到達イベントがあれば返す"""
        if not self.is_alive:
            return None

        if self.atb.status in (GaugeStatus.CHARGING, GaugeStatus.COOLDOWN):
            self.effects.update(dt)

        is_paused = self.is_stopped
        event = self.atb.advance(dt, is_paused=is_paused)

        if event == ATBEvent.COOLED:
            self.enter_ready()

        return event

    def set_command(self, command: 'BattleCommand'):
        """コマンドをセットし、充填を開始する"""
        self.current_command = command
        duration = 1.0
        if isinstance(command, PartCommand):
            part = self._parts.get(command.part_type)
            if part:
                duration = part.calculate_charge_duration()
        self.atb.start_charge(duration)

    def start_execution(self):
        """行動実行ラインに到達：構えを解除し実行状態へ"""
        self.effects.clear_stances()
        self.atb.start_execution()

    def enter_cooldown(self, interrupted: bool = False):
        self.atb.enter_cooldown(interrupted=interrupted)

    def enter_ready(self):
        self.current_command = None
        self.atb.enter_ready()

    # === 自己診断（パーツ検証・割り込み・身代わり判定） ===

    def validate_actionable_part(
        self, part_type: PartType
    ) -> Tuple[Optional[Part], ExecutionOutcome]:
        """【Tell, Don't Ask】指定部位で行動を実行可能か自己診断する"""
        part = self._parts.get(part_type)
        if not part or not part.is_alive:
            return None, ExecutionOutcome.PART_UNUSABLE
        if not part.is_implemented:
            return None, ExecutionOutcome.ACTION_UNIMPLEMENTED
        if self.is_part_stopped(part_type):
            return None, ExecutionOutcome.PART_STOPPED
        return part, ExecutionOutcome.OK

    def evaluate_interruption(self) -> Optional[ExecutionOutcome]:
        """【Tell, Don't Ask】充填中の自身の状態およびターゲットを自己診断し、中断理由があれば返す"""
        if not self.is_alive or not self.is_charging:
            return None

        cmd = self.current_part_command
        if not cmd:
            return None

        part = self._parts.get(cmd.part_type)
        if not part or not part.is_alive:
            return ExecutionOutcome.RESERVED_PART_DESTROYED

        if part.locks_target:
            target = cmd.target_robot
            if target and not target.is_alive:
                return ExecutionOutcome.TARGET_LOST
            if part.targets_part and cmd.target_part:
                if not target or not target.is_part_alive(cmd.target_part):
                    return ExecutionOutcome.TARGET_LOST

        return None

    def can_intercept(self, target_robot: 'Robot') -> bool:
        """対象の味方機への攻撃を自身が身代わり（ブロック）できるか"""
        return (
            self.team == target_robot.team
            and self is not target_robot
            and self.is_alive
            and self.effects.is_blocking()
        )

    def trigger_trap_if_applicable(self, traps: TrapManager) -> Tuple[Optional[InstalledTrap], bool]:
        """充填完了時にトラップが発動するか自己検証し、被弾処理を行う"""
        cmd = self.current_part_command
        if not cmd:
            return None, False

        part = self._parts.get(cmd.part_type)
        if not part or not part.is_alive:
            return None, False

        triggered_trap = traps.trigger(self.team, part.action)
        if triggered_trap is None:
            return None, False

        is_destroyed = part.take_damage(triggered_trap.damage)
        return triggered_trap, is_destroyed

    # === 戦闘スナップショットの生成（計算層へ渡すイミュータブルデータ） ===

    def to_participant(self, active_part: Optional[Part] = None) -> BattleParticipant:
        """現在の機体状態から、戦闘計算用の動的スナップショットを生成する。"""
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

        defensive_action_def = self._resolve_defensive_action_def()

        return BattleParticipant(
            stats=stats,
            legs_stats=self.get_legs_stats(),
            parts_hp=self.get_parts_hp(),
            defensive_info=DefensiveInfo(
                gauge_status=self.gauge_status,
                action_def=defensive_action_def,
            ),
            buff_success=self.effects.get_buff_success(),
            damage_reduction=self.effects.get_protect_reduction(self.is_part_alive),
        )

    def _resolve_defensive_action_def(self) -> Optional[ActionDefinition]:
        """被弾時に防御ペナルティを生む直前の予約行動形式を取得する"""
        part = self.current_part
        return part.action_def if part else None

    # === 自立的な状態更新（Tell, Don't Ask） ===

    def apply_damage(self, part_type: PartType, amount: int) -> Tuple[int, bool]:
        """指定部位にダメージを適用し、(実効ダメージ量, 破壊されたか) を返す"""
        part = self._parts.get(part_type)
        if not part or not part.is_alive:
            return 0, False
        hp_before = part.hp
        is_destroyed = part.take_damage(amount)
        return min(amount, hp_before), is_destroyed

    def apply_repair(
        self, amount: int, specific_part: PartType
    ) -> Optional[Tuple[PartType, int]]:
        """装甲を修復する。"""
        part = self._parts.get(specific_part)
        if part and part.is_alive:
            actual = part.repair(amount)
            return (specific_part, actual) if actual > 0 else None
        return None

    def apply_restore(self, specific_part: PartType) -> Optional[PartType]:
        """指定部位を復活させる。"""
        part = self._parts.get(specific_part)
        if part and part.is_broken:
            if part.restore():
                return specific_part
        return None

    def apply_status(self, effect: StatusEffect):
        """状態異常・バフを自身に付与する"""
        self.effects.add(effect)

    def on_action_completed(self) -> List[StatusEffect]:
        """【Tell, Don't Ask】行動完了に伴う機体状態の後処理（攻撃バフの消費など）を行い、終了した効果を返す"""
        part = self.current_part
        if part and part.skill_kind == SkillKind.ATTACK:
            return self.effects.consume_attack_charges()
        return []