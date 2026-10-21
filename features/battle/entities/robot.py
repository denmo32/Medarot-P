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
    RobotSnapshot,
    StatusEffect,
    TargetPartInfo,
)
from domain.traps import InstalledTrap, TrapManager

from .atb_track import ATBEvent, ATBTrack
from .commands import ExecutionOutcome, PartCommand
from .effect_tracker import EffectTracker
from .part import Part

if TYPE_CHECKING:
    from .commands import BattleCommand


class Robot:
    def __init__(
        self,
        team: TeamType,
        is_leader: bool,
        name: str,
        medal_data: MedalData,
        parts: Dict[PartType, Part],
        medal_id: str = "",
    ):
        self.team = team
        self.is_leader = is_leader
        self.name = name
        self.medal_data = medal_data
        self.medal_id = medal_id
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

    # === ATB ライフサイクル (Tell, Don't Ask) ===

    def tick(self, dt: float) -> Optional[ATBEvent]:
        """1フレーム分の時間を進行させる。"""
        if not self.is_alive:
            return None

        if self.atb.status in (GaugeStatus.CHARGING, GaugeStatus.COOLDOWN):
            self.effects.update(dt)

        is_paused = self.is_stopped
        return self.atb.advance(dt, is_paused=is_paused)

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

    def finish_execution_to_cooldown(self):
        """物理軌道1: 中央実行ライン(1.0)からの放熱開始。
        行動完了、または中央ラインでの不発・トラップ破壊等により端から自陣へ向かう。
        """
        self.atb.enter_cooldown_from_execution()

    def abort_charging_to_cooldown(self):
        """物理軌道2: 充填トラック途中(pos)からの緊急反転後退。
        充填中のパーツ破壊・ターゲット喪失により、現在位置から直ちに自陣へ後退する。
        """
        self.atb.abort_charge_to_cooldown()

    def enter_ready(self):
        """放熱完了に伴い、予約コマンドを消去して待機状態へ戻る"""
        self.current_command = None
        self.atb.enter_ready()

    # === 自己診断（パーツ検証・割り込み・身代わり判定） ===

    def can_execute_part(self, part_type: PartType) -> bool:
        """【Tell, Don't Ask】指定部位が存在し、行動実行可能（生存かつ実装済み）かを自己診断する"""
        part = self._parts.get(part_type)
        return part.can_execute if part else False

    def get_actionable_part_types(self) -> List[PartType]:
        """【Tell, Don't Ask】コマンド選択可能な部位（頭・右腕・左腕）のうち、実行可能な部位一覧を返す"""
        return [pt for pt in ACTIONABLE_PART_TYPES if self.can_execute_part(pt)]

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