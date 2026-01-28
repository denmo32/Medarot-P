"""戦闘計算ロジック（旧 CombatService）"""

import random
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, List
from battle.constants import PartType
from components.battle_component import StatusEffect
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
class CombatResult:
    is_hit: bool
    is_critical: bool
    is_defense: bool
    damage: int
    hit_part: Optional[str]
    added_effects: List[StatusEffect]

class CombatMechanics:
    """戦闘の命中・ダメージ計算を統括する"""

    @staticmethod
    def calculate_combat_result(world, attacker_id: int, target_id: int, 
                              target_desired_part: Optional[str], 
                              attacker_part_type: str) -> Optional[CombatResult]:
        
        attacker_comps = world.try_get_entity(attacker_id)
        target_comps = world.try_get_entity(target_id)
        if not attacker_comps or not target_comps: return None

        # 攻撃パーツ情報の取得
        atk_part_id = attacker_comps['partlist'].parts.get(attacker_part_type)
        atk_part_comps = world.try_get_entity(atk_part_id) if atk_part_id else None
        if not atk_part_comps or 'attack' not in atk_part_comps: return None
            
        attack_comp = atk_part_comps['attack']

        # 1. ステータス補正
        stats = CombatMechanics._calculate_adjusted_stats(world, attacker_comps, atk_part_comps, target_comps)
        
        # 2. 防御ペナルティ判定
        penalty = CombatMechanics._get_target_defensive_penalty(world, target_comps)

        # 3. 命中判定
        if penalty['force_hit']:
            hit_prob = 1.0
            is_hit = True
        else:
            hit_prob = calculate_hit_probability(stats['success'], stats['tgt_mobility'])
            is_hit = check_is_hit(hit_prob)
        
        if not is_hit:
            return CombatMechanics._create_result(False, False, False, 0, None, [])
        
        # 4. 詳細計算
        return CombatMechanics._calculate_hit_outcome(
            world, attack_comp, stats, hit_prob, target_comps, target_desired_part, penalty
        )

    @staticmethod
    def _calculate_adjusted_stats(world, attacker_comps, atk_part_comps, target_comps) -> Dict[str, int]:
        attack_comp = atk_part_comps['attack']
        my_mobility, my_defense = CombatMechanics._get_legs_stats(world, attacker_comps)

        # 属性相性
        atk_medal_attr = attacker_comps['medal'].attribute
        atk_part_attr = atk_part_comps['part'].attribute
        tgt_medal_attr = target_comps['medal'].attribute
        atk_bonus, def_bonus = AttributeLogic.calculate_affinity_bonus(atk_medal_attr, atk_part_attr, tgt_medal_attr)

        # スキル補正 (Registry)
        skill_behavior = SkillRegistry.get(attack_comp.skill_type)
        skill_success_bonus, skill_attack_bonus = skill_behavior.get_offensive_bonuses(my_mobility, my_defense)

        tgt_mobility, tgt_defense = CombatMechanics._get_legs_stats(world, target_comps)

        return {
            'success': max(1, attack_comp.success + atk_bonus + skill_success_bonus),
            'attack': max(1, attack_comp.attack + atk_bonus + skill_attack_bonus),
            'tgt_mobility': max(0, tgt_mobility + def_bonus),
            'tgt_defense': max(0, tgt_defense + def_bonus)
        }

    @staticmethod
    def _get_target_defensive_penalty(world, target_comps) -> Dict[str, bool]:
        tgt_gauge = target_comps.get('gauge')
        prevent_defense, force_hit, force_critical = False, False, False

        if tgt_gauge and tgt_gauge.selected_part:
            tgt_part_id = target_comps['partlist'].parts.get(tgt_gauge.selected_part)
            tgt_p_comps = world.try_get_entity(tgt_part_id)
            if tgt_p_comps and 'attack' in tgt_p_comps:
                # Registry委譲
                skill_behavior = SkillRegistry.get(tgt_p_comps['attack'].skill_type)
                prevent_defense, force_hit, force_critical = skill_behavior.get_defensive_penalty(tgt_gauge.status)
        
        return {
            'prevent_defense': prevent_defense,
            'force_hit': force_hit,
            'force_critical': force_critical
        }

    @staticmethod
    def _calculate_hit_outcome(world, attack_comp, stats, hit_prob, target_comps, target_desired_part, penalty) -> CombatResult:
        if penalty['force_critical']:
            is_critical = True
            is_defense = False
        else:
            break_prob = calculate_break_probability(stats['success'], stats['tgt_defense'])
            is_critical, is_defense = check_attack_outcome(hit_prob, break_prob)
            if penalty['prevent_defense']:
                is_defense = False

        hit_part = CombatMechanics._determine_hit_part(world, target_comps, target_desired_part, is_defense)
        
        damage = calculate_damage(
            stats['attack'], stats['success'], stats['tgt_mobility'], stats['tgt_defense'], 
            is_critical, is_defense
        )
        
        # 特性による追加効果 (Registry)
        trait_behavior = TraitRegistry.get(attack_comp.trait)
        added_effects = trait_behavior.get_added_effects(stats['success'], stats['tgt_mobility'])

        return CombatMechanics._create_result(True, is_critical, is_defense, damage, hit_part, added_effects)

    @staticmethod
    def _create_result(is_hit, is_critical, is_defense, damage, hit_part, added_effects) -> CombatResult:
        return CombatResult(is_hit, is_critical, is_defense, damage, hit_part, added_effects)

    @staticmethod
    def _get_legs_stats(world, comps) -> Tuple[int, int]:
        legs_id = comps['partlist'].parts.get(PartType.LEGS)
        legs_comps = world.try_get_entity(legs_id) if legs_id is not None else None
        if legs_comps:
            mob_comp = legs_comps.get('mobility')
            if mob_comp:
                return mob_comp.mobility, mob_comp.defense
        return 0, 0

    @staticmethod
    def _determine_hit_part(world, target_comps, desired_part, is_defense) -> str:
        alive_parts_map = {}
        for pt, pid in target_comps['partlist'].parts.items():
             p_comps = world.try_get_entity(pid)
             if p_comps and p_comps['health'].hp > 0:
                 alive_parts_map[pt] = pid
                 
        alive_keys = list(alive_parts_map.keys())

        if is_defense:
            non_head = [p for p in alive_keys if p != PartType.HEAD]
            if non_head:
                non_head.sort(key=lambda p: world.entities[alive_parts_map[p]]['health'].hp, reverse=True)
                return non_head[0]
            return PartType.HEAD
        else:
            if desired_part and desired_part in alive_keys:
                return desired_part
            elif alive_keys:
                return random.choice(alive_keys)
        return PartType.HEAD