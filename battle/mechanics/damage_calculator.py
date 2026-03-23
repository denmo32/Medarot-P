"""ダメージ計算に関する戦闘計算ロジック"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any
from components.battle_component import StatusEffect, AttackComponent
from battle.mechanics.trait import TraitRegistry
from battle.mechanics.targeting import TargetingMechanics
from domain.combat_formula import calculate_break_probability, check_attack_outcome, calculate_damage


@dataclass
class AttackQuality:
    """攻撃の性質（クリティカル・防御）"""
    is_critical: bool
    is_defense: bool


@dataclass
class DamageCalculationContext:
    """ダメージ計算のコンテキスト"""
    attack_comp: AttackComponent
    success: int
    attack: int
    tgt_mobility: int
    tgt_defense: int
    hit_prob: float
    target_comps: Dict[str, Any]
    target_desired_part: Optional[str]
    prevent_defense: bool


class DamageCalculator:
    """
    ダメージ計算と攻撃結果の決定を担当する。
    
    責任範囲:
    - クリティカル・防御判定
    - 被弾部位の決定
    - ダメージ値の計算
    - 特性による追加効果の適用
    """

    @staticmethod
    def calculate_damage_result(
        attack_comp: AttackComponent,
        stats: Any,  # CombatStats
        hit_prob: float,
        target_part_hps: Dict[str, int],
        target_desired_part: Optional[str],
        prevent_defense: bool
    ) -> 'DamageResult':
        """
        命中確定後のダメージ結果を計算する。

        Args:
            attack_comp: 攻撃コンポーネント
            stats: 補正後のステータス（CombatStats）
            hit_prob: 命中確率
            target_part_hps: 対象のパーツとその HP の辞書
            target_desired_part: 指定部位
            prevent_defense: 防御不能フラグ

        Returns:
            ダメージ計算結果
        """
        # 1. 攻撃性質（クリティカル・防御）の決定
        quality = DamageCalculator._evaluate_attack_quality(
            stats.success, stats.tgt_defense, hit_prob, prevent_defense
        )

        # 2. 被弾部位の決定
        hit_part = TargetingMechanics.resolve_hit_part(
            target_part_hps,
            target_desired_part,
            quality.is_defense
        )

        # 3. ダメージ計算
        damage = calculate_damage(
            stats.attack, stats.success, stats.tgt_mobility, stats.tgt_defense,
            quality.is_critical, quality.is_defense
        )

        # 4. 特性（サンダー等）による追加効果
        trait_behavior = TraitRegistry.get(attack_comp.trait)
        added_effects = trait_behavior.get_added_effects(stats.success, stats.tgt_mobility)

        return DamageResult(
            is_critical=quality.is_critical,
            is_defense=quality.is_defense,
            damage=damage,
            hit_part=hit_part,
            added_effects=added_effects
        )

    @staticmethod
    def _evaluate_attack_quality(
        success: int,
        tgt_defense: int,
        hit_prob: float,
        prevent_defense: bool,
        force_critical: bool = False
    ) -> AttackQuality:
        """
        クリティカルか、防御成功かを判定する。
        
        Args:
            success: 攻撃側の成功度
            tgt_defense: 対象の防御力
            hit_prob: 命中確率
            prevent_defense: 防御不能フラグ
            force_critical: 強制クリティカルフラグ
            
        Returns:
            攻撃の性質
        """
        if force_critical:
            return AttackQuality(is_critical=True, is_defense=False)

        break_prob = calculate_break_probability(success, tgt_defense)
        is_critical, is_defense = check_attack_outcome(hit_prob, break_prob)

        # 防御不能ペナルティの適用
        if prevent_defense:
            is_defense = False

        return AttackQuality(is_critical=is_critical, is_defense=is_defense)


@dataclass
class DamageResult:
    """ダメージ計算の結果"""
    is_critical: bool
    is_defense: bool
    damage: int
    hit_part: str
    added_effects: List[StatusEffect] = field(default_factory=list)
