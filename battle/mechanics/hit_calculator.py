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
        world,
        attacker_comps: Dict[str, Any],
        atk_part_comps: Dict[str, Any],
        target_comps: Dict[str, Any]
    ) -> CombatStats:
        """
        ステータス、属性相性、スキルによる補正を一括計算する。
        
        Args:
            world: ECS ワールド
            attacker_comps: 攻撃側のコンポーネント
            atk_part_comps: 攻撃パーツのコンポーネント
            target_comps: 対象側のコンポーネント
            
        Returns:
            補正後のステータス値
        """
        attack_comp = atk_part_comps['attack']
        my_mob, my_def = HitCalculator._get_legs_stats(world, attacker_comps)
        tgt_mob, tgt_def = HitCalculator._get_legs_stats(world, target_comps)

        # 属性相性ボーナスの適用
        atk_bonus, def_bonus = AttributeLogic.calculate_affinity_bonus(
            attacker_comps['medal'].attribute,
            atk_part_comps['part'].attribute,
            target_comps['medal'].attribute
        )

        # スキル補正の適用
        skill_behavior = SkillRegistry.get(attack_comp.skill_type)
        s_success_bonus, s_attack_bonus = skill_behavior.get_offensive_bonuses(my_mob, my_def)

        return CombatStats(
            success=max(1, attack_comp.success + atk_bonus + s_success_bonus),
            attack=max(1, attack_comp.attack + atk_bonus + s_attack_bonus),
            tgt_mobility=max(0, tgt_mob + def_bonus),
            tgt_defense=max(0, tgt_def + def_bonus)
        )

    @staticmethod
    def get_defensive_penalty(world, target_comps: Dict[str, Any]) -> DefensivePenalty:
        """
        ターゲット側の状態（充填中等）による防御制限を取得する。
        
        Args:
            world: ECS ワールド
            target_comps: 対象のコンポーネント
            
        Returns:
            防御ペナルティ情報
        """
        tgt_gauge = target_comps.get('gauge')
        if not tgt_gauge or not tgt_gauge.selected_part:
            return DefensivePenalty()

        tgt_part_id = target_comps['partlist'].parts.get(tgt_gauge.selected_part)
        tgt_p_comps = world.try_get_entity(tgt_part_id)
        
        if not tgt_p_comps or 'attack' not in tgt_p_comps:
            return DefensivePenalty()

        # 相手が実行しようとしているスキルのペナルティ特性を参照
        skill_behavior = SkillRegistry.get(tgt_p_comps['attack'].skill_type)
        prevent_defense, force_hit, force_critical = skill_behavior.get_defensive_penalty(tgt_gauge.status)

        return DefensivePenalty(
            prevent_defense=prevent_defense,
            force_hit=force_hit,
            force_critical=force_critical
        )

    @staticmethod
    def calculate_hit_probability(stats: CombatStats, penalty: DefensivePenalty) -> Tuple[float, bool]:
        """
        命中確率を計算し、命中可否を判定する。
        
        Args:
            stats: 補正後のステータス
            penalty: 防御ペナルティ
            
        Returns:
            (命中確率, 命中したか) のタプル
        """
        if penalty.force_hit:
            return 1.0, True

        hit_prob = calculate_hit_probability(stats.success, stats.tgt_mobility)
        from domain.combat_formula import check_is_hit
        is_hit = check_is_hit(hit_prob)
        
        return hit_prob, is_hit

    @staticmethod
    def _get_legs_stats(world, comps: Dict[str, Any]) -> Tuple[int, int]:
        """脚部パーツの機動・防御値を取得する。"""
        legs_id = comps['partlist'].parts.get(PartType.LEGS)
        legs_comps = world.try_get_entity(legs_id) if legs_id is not None else None
        
        if legs_comps and 'mobility' in legs_comps:
            return legs_comps['mobility'].mobility, legs_comps['mobility'].defense
        return 0, 0
