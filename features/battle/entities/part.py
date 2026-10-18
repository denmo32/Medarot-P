"""パーツ個別の性能計算、状態管理、HP変動を自律して担うエンティティ。"""
from typing import Optional
from domain.action_logic import ActionDefinition, get_action_definition
from domain.attribute import get_passive_bonuses
from domain.constants import (
    ActionType,
    AttributeType,
    HitPolicy,
    PartType,
    SkillKind,
    SkillPresentation,
    SkillType,
    TargetRule,
    TargetTiming,
)
from domain.gauge_utils import calculate_base_time
from domain.models import (
    ActionResult,
    EffectResolutionContext,
    MedalData,
    PartCombatStats,
    PartData,
)
from domain.skills import SkillDefinition, get_skill_definition


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