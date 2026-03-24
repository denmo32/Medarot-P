"""戦闘計算ロジック - 統合インターフェース"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from components.battle_component import StatusEffect
from battle.mechanics.hit_calculator import (
    HitCalculator, CombatStats, DefensivePenalty,
    AttackParams, MedalParams, LegsStats
)
from battle.mechanics.damage_calculator import DamageCalculator, DamageResult


@dataclass
class CombatResult:
    """戦闘計算の結果"""
    is_hit: bool
    is_critical: bool = False
    is_defense: bool = False
    damage: int = 0
    hit_part: Optional[str] = None
    added_effects: list = field(default_factory=list)

    @classmethod
    def miss(cls) -> 'CombatResult':
        """ミス時の結果を生成"""
        return cls(is_hit=False)


class CombatMechanics:
    """
    戦闘の命中・ダメージ計算を統括するファサード。

    実際の計算は HitCalculator と DamageCalculator に委譲する。
    """

    @staticmethod
    def calculate_combat_result(
        attacker_medal: MedalParams,
        attacker_part: AttackParams,
        attacker_legs: LegsStats,
        target_medal: MedalParams,
        target_legs: LegsStats,
        target_gauge_status: str,
        target_selected_part: Optional[str],
        target_part_skill_type: Optional[str],
        target_part_hps: Dict[str, int],
        target_desired_part: Optional[str]
    ) -> Optional[CombatResult]:
        """
        戦闘計算のメインエントリーポイント。
        
        Args:
            attacker_medal: 攻撃者のメダルパラメータ
            attacker_part: 攻撃パーツのパラメータ
            attacker_legs: 攻撃者の脚部ステータス
            target_medal: 対象のメダルパラメータ
            target_legs: 対象の脚部ステータス
            target_gauge_status: 対象のゲージ状態
            target_selected_part: 対象の選択中パーツ
            target_part_skill_type: 対象の選択中パーツのスキル種別
            target_part_hps: 対象の生存パーツ HP {part_type: hp}
            target_desired_part: 指定部位
        
        Returns:
            戦闘計算結果。計算不能な場合は None。
        """
        # 1. パラメータ補正とペナルティの取得（HitCalculator へ委譲）
        stats = HitCalculator.calculate_adjusted_stats(
            attacker_medal=attacker_medal,
            attacker_part=attacker_part,
            attacker_legs=attacker_legs,
            target_medal=target_medal,
            target_legs=target_legs
        )

        penalty = HitCalculator.get_defensive_penalty(
            target_gauge_status=target_gauge_status,
            target_selected_part=target_selected_part,
            target_part_skill_type=target_part_skill_type
        )

        # 2. 命中判定（HitCalculator へ委譲）
        hit_prob, is_hit = HitCalculator.calculate_hit_probability(stats, penalty)
        if not is_hit:
            return CombatResult.miss()

        # 3. ダメージ計算（DamageCalculator へ委譲）
        damage_result = DamageCalculator.calculate_damage_result(
            attack_comp=attacker_part.to_attack_component(),
            stats=stats,
            hit_prob=hit_prob,
            target_part_hps=target_part_hps,
            target_desired_part=target_desired_part,
            prevent_defense=penalty.prevent_defense
        )

        return CombatResult(
            is_hit=True,
            is_critical=damage_result.is_critical,
            is_defense=damage_result.is_defense,
            damage=damage_result.damage,
            hit_part=damage_result.hit_part,
            added_effects=damage_result.added_effects
        )
