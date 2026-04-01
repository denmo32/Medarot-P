"""命中判定に関する戦闘計算ロジック"""

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from battle.constants import PartType
from components.battle_component import AttackComponent
from domain.attribute import AttributeLogic
from battle.mechanics.skill import SkillRegistry
from domain.combat_formula import calculate_hit_probability


@dataclass(frozen=True)
class CombatStats:
    """戦闘計算に使用するステータス値"""
    success: int
    attack: int
    tgt_mobility: int
    tgt_defense: int


@dataclass(frozen=True)
class DefensivePenalty:
    """ターゲット側の防御制限ペナルティ"""
    prevent_defense: bool = False
    force_hit: bool = False
    force_critical: bool = False


@dataclass(frozen=True)
class AttackParams:
    """攻撃側の計算パラメータ"""
    success: int
    attack: int
    part_attribute: str
    skill_type: str
    trait: str = ""
    
    def to_attack_component(self) -> 'AttackComponent':
        """AttackComponent を生成する（ダミー値を使用）"""
        # DamageCalculator.get_added_effects は trait のみを使用するため、
        # 他のフィールドはダミー値で問題ない
        return AttackComponent(
            success=self.success,
            attack=self.attack,
            skill_type=self.skill_type,
            trait=self.trait
        )


@dataclass(frozen=True)
class MedalParams:
    """メダルのパラメータ"""
    attribute: str


@dataclass(frozen=True)
class LegsStats:
    """脚部パーツのステータス"""
    mobility: int
    defense: int


class HitCalculator:
    """
    命中判定と攻撃パラメータの補正計算を担当する。

    責任範囲:
    - 属性・スキルによるステータス補正
    - 防御ペナルティの計算
    - 命中判定の実行
    """

    @staticmethod
    def calculate_adjusted_stats(
        attacker_medal: MedalParams,
        attacker_part: AttackParams,
        attacker_legs: LegsStats,
        target_medal: MedalParams,
        target_legs: LegsStats
    ) -> CombatStats:
        """
        ステータス、属性相性、スキルによる補正を一括計算する。
        
        Args:
            attacker_medal: 攻撃者のメダルパラメータ
            attacker_part: 攻撃パーツのパラメータ
            attacker_legs: 攻撃者の脚部ステータス
            target_medal: 対象のメダルパラメータ
            target_legs: 対象の脚部ステータス
        
        Returns:
            補正後の戦闘ステータス
        """
        # 属性相性ボーナスの適用
        atk_bonus, def_bonus = AttributeLogic.calculate_affinity_bonus(
            attacker_medal.attribute,
            attacker_part.part_attribute,
            target_medal.attribute
        )

        # スキル補正の適用
        skill_behavior = SkillRegistry.get(attacker_part.skill_type)
        s_success_bonus, s_attack_bonus = skill_behavior.get_offensive_bonuses(
            attacker_legs.mobility,
            attacker_legs.defense
        )

        return CombatStats(
            success=max(1, attacker_part.success + atk_bonus + s_success_bonus),
            attack=max(1, attacker_part.attack + atk_bonus + s_attack_bonus),
            tgt_mobility=max(0, target_legs.mobility + def_bonus),
            tgt_defense=max(0, target_legs.defense + def_bonus)
        )

    @staticmethod
    def get_defensive_penalty(
        target_gauge_status: str,
        target_selected_part: Optional[str],
        target_part_skill_type: Optional[str]
    ) -> DefensivePenalty:
        """
        ターゲット側の状態（充填中等）による防御制限を取得する。
        
        Args:
            target_gauge_status: 対象のゲージ状態
            target_selected_part: 対象の選択中パーツ
            target_part_skill_type: 対象の選択中パーツのスキル種別
        
        Returns:
            防御ペナルティ情報
        """
        if not target_gauge_status or not target_selected_part or not target_part_skill_type:
            return DefensivePenalty()

        # 相手が実行しようとしているスキルのペナルティ特性を参照
        skill_behavior = SkillRegistry.get(target_part_skill_type)
        prevent_defense, force_hit, force_critical = skill_behavior.get_defensive_penalty(target_gauge_status)

        return DefensivePenalty(
            prevent_defense=prevent_defense,
            force_hit=force_hit,
            force_critical=force_critical
        )

    @staticmethod
    def calculate_hit_probability(stats: CombatStats, penalty: DefensivePenalty) -> Tuple[float, bool]:
        """
        命中確率を計算し、命中可否を判定する。
        """
        if penalty.force_hit:
            return 1.0, True

        hit_prob = calculate_hit_probability(stats.success, stats.tgt_mobility)
        from domain.combat_formula import check_is_hit
        is_hit = check_is_hit(hit_prob)

        return hit_prob, is_hit
