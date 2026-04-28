"""戦闘計算ロジック - 統合インターフェース"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from battle.mechanics.hit_calculator import (
    HitCalculator, AttackParams, MedalParams, LegsStats
)
from battle.mechanics.damage_calculator import DamageCalculator, CombatResult
from domain.constants import PartType
from battle.mechanics.targeting import TargetingMechanics

if TYPE_CHECKING:
    from core.ecs import World

class CombatParamsBuilder:
    """
    ECS の World から戦闘計算に必要なパラメータを抽出するビルダー（純粋関数的ヘルパー）。
    System がドメイン知識を持ちすぎないようにするための抽象化レイヤー。
    """
    
    @staticmethod
    def build_attacker_medal(world: "World", attacker_eid: int) -> Optional[MedalParams]:
        comps = world.try_get_entity(attacker_eid)
        if not comps or 'medal' not in comps:
            return None
        return MedalParams(attribute=comps['medal'].attribute)

    @staticmethod
    def build_attacker_part(world: "World", attacker_eid: int, part_type: str) -> Optional[AttackParams]:
        comps = world.try_get_entity(attacker_eid)
        if not comps or 'partlist' not in comps:
            return None
        
        part_id = comps['partlist'].parts.get(part_type)
        if not part_id:
            return None
            
        p_comps = world.try_get_entity(part_id)
        if not p_comps or 'attack' not in p_comps or 'part' not in p_comps:
            return None
            
        attack_comp = p_comps['attack']
        part_comp = p_comps['part']
        
        return AttackParams(
            success=attack_comp.success,
            attack=attack_comp.attack,
            part_attribute=part_comp.attribute,
            skill_type=attack_comp.skill_type,
            trait=attack_comp.trait
        )

    @staticmethod
    def build_legs_stats(world: "World", entity_eid: int) -> LegsStats:
        comps = world.try_get_entity(entity_eid)
        if comps and 'partlist' in comps:
            legs_id = comps['partlist'].parts.get(PartType.LEGS)
            if legs_id:
                legs_comps = world.try_get_entity(legs_id)
                if legs_comps and 'mobility' in legs_comps:
                    return LegsStats(
                        mobility=legs_comps['mobility'].mobility,
                        defense=legs_comps['mobility'].defense
                    )
        return LegsStats(mobility=0, defense=0)

    @staticmethod
    def build_target_medal(world: "World", target_id: int) -> Optional[MedalParams]:
        comps = world.try_get_entity(target_id)
        if not comps or 'medal' not in comps:
            return None
        return MedalParams(attribute=comps['medal'].attribute)

    @staticmethod
    def get_target_gauge_data(world: "World", target_id: int) -> tuple[str, Optional[str], Optional[str]]:
        """(status, selected_part, skill_type) を返す"""
        comps = world.try_get_entity(target_id)
        if not comps:
            return "", None, None
            
        gauge = comps.get('gauge')
        status = gauge.status if gauge else ""
        selected_part = gauge.selected_part if gauge else None
        
        skill_type = None
        if selected_part and 'partlist' in comps:
            part_id = comps['partlist'].parts.get(selected_part)
            if part_id:
                p_comps = world.try_get_entity(part_id)
                if p_comps and 'attack' in p_comps:
                    skill_type = p_comps['attack'].skill_type
                    
        return status, selected_part, skill_type


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
        return DamageCalculator.calculate_damage_result(
            attack_comp=attacker_part.to_attack_component(),
            stats=stats,
            hit_prob=hit_prob,
            target_part_hps=target_part_hps,
            target_desired_part=target_desired_part,
            prevent_defense=penalty.prevent_defense
        )
