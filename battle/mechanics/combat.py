"""戦闘計算ロジック - 統合インターフェース"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from components.battle_component import StatusEffect
from battle.mechanics.hit_calculator import HitCalculator, CombatStats, DefensivePenalty
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
        state,
        attacker_id: int,
        target_id: int,
        target_desired_part: Optional[str],
        attacker_part_type: str
    ) -> Optional[CombatResult]:
        """
        戦闘計算のメインエントリーポイント。
        """
        # 1. パラメータ補正とペナルティの取得（HitCalculator へ委譲）
        try:
            stats = HitCalculator.calculate_adjusted_stats(
                state, attacker_id, attacker_part_type, target_id
            )
        except ValueError:
            return None

        penalty = HitCalculator.get_defensive_penalty(state, target_id)

        # 2. 命中判定（HitCalculator へ委譲）
        hit_prob, is_hit = HitCalculator.calculate_hit_probability(stats, penalty)
        if not is_hit:
            return CombatResult.miss()

        # 3. ダメージ計算（DamageCalculator へ委譲）
        target_part_hps = state.get_alive_parts_hp(target_id)
        
        # 攻撃パーツのコンポーネント取得（ダメージ計算用）
        atk_part_comps = state.get_part_components(attacker_id, attacker_part_type, 'attack')
        if not atk_part_comps:
            return None
        attack_comp = atk_part_comps['attack']

        damage_result = DamageCalculator.calculate_damage_result(
            attack_comp=attack_comp,
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
