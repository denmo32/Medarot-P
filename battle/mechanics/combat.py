"""戦闘計算ロジック"""

import random
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, List, Any
from battle.constants import PartType
from components.battle_component import StatusEffect, AttackComponent
from domain.attribute import AttributeLogic
from battle.mechanics.trait import TraitRegistry
from battle.mechanics.skill import SkillRegistry
from domain.combat_formula import (
    calculate_hit_probability, 
    calculate_break_probability, 
    check_is_hit,
    check_attack_outcome,
    calculate_damage
)

@dataclass
class AdjustedStats:
    """属性やスキルによる補正適用後の戦闘パラメータ"""
    success: int
    attack: int
    tgt_mobility: int
    tgt_defense: int

@dataclass
class CombatResult:
    is_hit: bool
    is_critical: bool = False
    is_defense: bool = False
    damage: int = 0
    hit_part: Optional[str] = None
    added_effects: List[StatusEffect] = field(default_factory=list)

    @classmethod
    def miss(cls):
        """ミス時の結果を生成"""
        return cls(is_hit=False)

@dataclass
class HitOutcomeContext:
    """計算プロセス間で共有されるコンテキスト"""
    world: Any
    attack_comp: AttackComponent
    stats: AdjustedStats
    hit_prob: float
    target_comps: Dict[str, Any]
    target_desired_part: Optional[str]
    penalty: Dict[str, bool]

class CombatMechanics:
    """
    戦闘の命中・ダメージ計算を統括する。
    計算プロセスをフェーズ分割することで、拡張性を高めている。
    """

    @staticmethod
    def calculate_combat_result(world, attacker_id: int, target_id: int, 
                              target_desired_part: Optional[str], 
                              attacker_part_type: str) -> Optional[CombatResult]:
        """戦闘計算のメインエントリーポイント"""
        
        # 1. データの準備と事前検証
        attacker_comps = world.try_get_entity(attacker_id)
        target_comps = world.try_get_entity(target_id)
        if not attacker_comps or not target_comps:
            return None

        atk_part_id = attacker_comps['partlist'].parts.get(attacker_part_type)
        atk_part_comps = world.try_get_entity(atk_part_id) if atk_part_id else None
        if not atk_part_comps or 'attack' not in atk_part_comps:
            return None
        
        attack_comp = atk_part_comps['attack']

        # 2. パラメータ補正フェーズ
        stats = CombatMechanics._calculate_adjusted_stats(world, attacker_comps, atk_part_comps, target_comps)
        penalty = CombatMechanics._get_target_defensive_penalty(world, target_comps)

        # 3. 命中判定フェーズ
        hit_prob = 1.0 if penalty['force_hit'] else calculate_hit_probability(stats.success, stats.tgt_mobility)
        
        if not penalty['force_hit'] and not check_is_hit(hit_prob):
            return CombatResult.miss()
        
        # 4. 結果確定フェーズ
        ctx = HitOutcomeContext(
            world=world,
            attack_comp=attack_comp,
            stats=stats,
            hit_prob=hit_prob,
            target_comps=target_comps,
            target_desired_part=target_desired_part,
            penalty=penalty
        )
        return CombatMechanics._determine_hit_outcome(ctx)

    @staticmethod
    def _calculate_adjusted_stats(world, attacker_comps, atk_part_comps, target_comps) -> AdjustedStats:
        """ステータス、属性相性、スキルによる補正を一括計算"""
        attack_comp = atk_part_comps['attack']
        my_mob, my_def = CombatMechanics._get_legs_stats(world, attacker_comps)
        tgt_mob, tgt_def = CombatMechanics._get_legs_stats(world, target_comps)

        # 属性相性ボーナス
        atk_medal_attr = attacker_comps['medal'].attribute
        atk_part_attr = atk_part_comps['part'].attribute
        tgt_medal_attr = target_comps['medal'].attribute
        atk_bonus, def_bonus = AttributeLogic.calculate_affinity_bonus(atk_medal_attr, atk_part_attr, tgt_medal_attr)

        # スキル補正 (SkillBehaviorに委譲)
        skill_behavior = SkillRegistry.get(attack_comp.skill_type)
        s_success_bonus, s_attack_bonus = skill_behavior.get_offensive_bonuses(my_mob, my_def)

        return AdjustedStats(
            success=max(1, attack_comp.success + atk_bonus + s_success_bonus),
            attack=max(1, attack_comp.attack + atk_bonus + s_attack_bonus),
            tgt_mobility=max(0, tgt_mob + def_bonus),
            tgt_defense=max(0, tgt_def + def_bonus)
        )

    @staticmethod
    def _get_target_defensive_penalty(world, target_comps) -> Dict[str, bool]:
        """ターゲット側の状態による防御・回避ペナルティを取得"""
        tgt_gauge = target_comps.get('gauge')
        prevent_defense, force_hit, force_critical = False, False, False

        if tgt_gauge and tgt_gauge.selected_part:
            tgt_part_id = target_comps['partlist'].parts.get(tgt_gauge.selected_part)
            tgt_p_comps = world.try_get_entity(tgt_part_id)
            if tgt_p_comps and 'attack' in tgt_p_comps:
                skill_behavior = SkillRegistry.get(tgt_p_comps['attack'].skill_type)
                # 相手が充填中や放熱中の場合のペナルティを取得
                prevent_defense, force_hit, force_critical = skill_behavior.get_defensive_penalty(tgt_gauge.status)
        
        return {
            'prevent_defense': prevent_defense, 
            'force_hit': force_hit, 
            'force_critical': force_critical
        }

    @staticmethod
    def _determine_hit_outcome(ctx: HitOutcomeContext) -> CombatResult:
        """命中したことが確定した後の詳細計算（部位、ダメージ、効果）"""
        
        # 1. 攻撃の性質（クリティカル・防御）の決定
        if ctx.penalty['force_critical']:
            is_critical, is_defense = True, False
        else:
            break_prob = calculate_break_probability(ctx.stats.success, ctx.stats.tgt_defense)
            is_critical, is_defense = check_attack_outcome(ctx.hit_prob, break_prob)
            
            # 防御不能ペナルティの適用
            if ctx.penalty['prevent_defense']:
                is_defense = False

        # 2. 被弾部位の決定
        hit_part = CombatMechanics._resolve_hit_part(ctx, is_defense)
        
        # 3. ダメージ計算
        damage = calculate_damage(
            ctx.stats.attack, ctx.stats.success, ctx.stats.tgt_mobility, ctx.stats.tgt_defense, 
            is_critical, is_defense
        )
        
        # 4. 特性による追加効果の適用
        trait_behavior = TraitRegistry.get(ctx.attack_comp.trait)
        added_effects = trait_behavior.get_added_effects(ctx.stats.success, ctx.stats.tgt_mobility)

        return CombatResult(
            is_hit=True, 
            is_critical=is_critical, 
            is_defense=is_defense, 
            damage=damage, 
            hit_part=hit_part, 
            added_effects=added_effects
        )

    @staticmethod
    def _resolve_hit_part(ctx: HitOutcomeContext, is_defense: bool) -> str:
        """被弾部位の最終決定ロジック"""
        alive_parts = {
            pt: pid for pt, pid in ctx.target_comps['partlist'].parts.items() 
            if ctx.world.try_get_entity(pid)['health'].hp > 0
        }
        
        if not alive_parts:
            return PartType.HEAD

        # 防御時は、頭部を守るために他の部位を優先する
        if is_defense:
            non_head = [pt for pt in alive_parts if pt != PartType.HEAD]
            if non_head:
                # 最もHPの高い部位を盾にする
                non_head.sort(key=lambda pt: ctx.world.entities[alive_parts[pt]]['health'].hp, reverse=True)
                return non_head[0]
            return PartType.HEAD
        
        # 狙い撃ちなどの指定部位が生存していれば、そこを狙う
        if ctx.target_desired_part in alive_parts:
            return ctx.target_desired_part
            
        return random.choice(list(alive_parts.keys()))

    @staticmethod
    def _get_legs_stats(world, comps) -> Tuple[int, int]:
        """脚部パーツの性能（機動、防御）を取得"""
        legs_id = comps['partlist'].parts.get(PartType.LEGS)
        legs_comps = world.try_get_entity(legs_id) if legs_id is not None else None
        if legs_comps and 'mobility' in legs_comps:
            return legs_comps['mobility'].mobility, legs_comps['mobility'].defense
        return 0, 0