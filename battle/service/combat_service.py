"""戦闘計算サービス"""

import random
from dataclasses import dataclass
from typing import Optional, Tuple
from battle.constants import PartType
from battle.domain.attributes import AttributeLogic
from battle.domain.traits import TraitManager
from battle.domain.skills import SkillManager
from battle.domain.calculator import (
    calculate_hit_probability, 
    calculate_break_probability, 
    check_is_hit,
    check_attack_outcome,
    calculate_damage
)

@dataclass
class CombatResult:
    """戦闘計算結果を保持するデータクラス"""
    is_hit: bool
    is_critical: bool
    is_defense: bool
    damage: int
    hit_part: Optional[str]
    stop_duration: float

class CombatService:
    """戦闘の命中・ダメージ計算を一括して行うサービス"""

    @staticmethod
    def calculate_combat_result(world, attacker_id: int, target_id: int, 
                              target_desired_part: Optional[str], 
                              attacker_part_type: str) -> Optional[CombatResult]:
        """
        戦闘結果を計算して返す
        """
        attacker_comps = world.try_get_entity(attacker_id)
        target_comps = world.try_get_entity(target_id)
        
        if not attacker_comps or not target_comps:
            return None

        # 攻撃パーツ情報の取得
        atk_part_id = attacker_comps['partlist'].parts.get(attacker_part_type)
        if not atk_part_id:
            return None
            
        atk_part_comps = world.try_get_entity(atk_part_id)
        if not atk_part_comps or 'attack' not in atk_part_comps:
            return None
            
        attack_comp = atk_part_comps['attack']

        # 自身の脚部性能（機動・防御）を取得
        my_mobility, my_defense = CombatService._get_legs_stats(world, attacker_comps)

        # 属性情報の取得
        atk_medal = attacker_comps.get('medal')
        atk_part = atk_part_comps.get('part')
        tgt_medal = target_comps.get('medal')
        
        atk_medal_attr = atk_medal.attribute if atk_medal else "undefined"
        atk_part_attr = atk_part.attribute if atk_part else "undefined"
        tgt_medal_attr = tgt_medal.attribute if tgt_medal else "undefined"

        # 相性補正の計算
        atk_bonus, def_bonus = AttributeLogic.calculate_affinity_bonus(atk_medal_attr, atk_part_attr, tgt_medal_attr)

        # --- 攻撃側のスキル補正加算 ---
        skill_behavior = SkillManager.get_behavior(attack_comp.skill_type)
        skill_success_bonus, skill_attack_bonus = skill_behavior.get_offensive_bonuses(my_mobility, my_defense)

        # ステータス補正適用 (最小値クリップ含む)
        adjusted_success = max(1, attack_comp.success + atk_bonus + skill_success_bonus)
        adjusted_attack = max(1, attack_comp.attack + atk_bonus + skill_attack_bonus)
        
        tgt_mobility, tgt_defense = CombatService._get_legs_stats(world, target_comps)
        adjusted_mobility = max(0, tgt_mobility + def_bonus)
        adjusted_defense = max(0, tgt_defense + def_bonus)

        # --- 防御側のペナルティ判定 ---
        prevent_defense = False
        force_hit = False
        force_critical = False

        tgt_gauge = target_comps.get('gauge')
        # ターゲットが使用中のパーツスキルを確認
        tgt_skill_type = None
        if tgt_gauge and tgt_gauge.selected_part:
            tgt_part_id = target_comps['partlist'].parts.get(tgt_gauge.selected_part)
            tgt_p_comps = world.try_get_entity(tgt_part_id)
            if tgt_p_comps and 'attack' in tgt_p_comps:
                tgt_skill_type = tgt_p_comps['attack'].skill_type
        
        if tgt_gauge and tgt_skill_type:
            tgt_skill_behavior = SkillManager.get_behavior(tgt_skill_type)
            prevent_defense, force_hit, force_critical = tgt_skill_behavior.get_defensive_penalty(tgt_gauge.status)

        # 命中判定
        if force_hit:
            hit_prob = 1.0
            is_hit = True
        else:
            hit_prob = calculate_hit_probability(adjusted_success, adjusted_mobility)
            is_hit = check_is_hit(hit_prob)
        
        if not is_hit:
            return CombatService._create_result_data(False, False, False, 0, None, 0.0)
        else:
            return CombatService._calculate_hit_outcome(
                world, attack_comp, adjusted_success, adjusted_attack, adjusted_mobility, adjusted_defense, 
                hit_prob, target_comps, target_desired_part,
                prevent_defense, force_critical
            )

    @staticmethod
    def _calculate_hit_outcome(world, attack_comp, success, attack_power, mobility, defense, hit_prob, target_comps, target_desired_part, prevent_defense, force_critical) -> CombatResult:
        """命中時の詳細計算（クリティカル、防御、ダメージ）を行う"""
        
        if force_critical:
            is_critical = True
            is_defense = False
        else:
            break_prob = calculate_break_probability(success, defense)
            is_critical, is_defense = check_attack_outcome(hit_prob, break_prob)
            
            if prevent_defense:
                is_defense = False

        # 命中部位の決定（防御時は部位置換）
        hit_part = CombatService._determine_hit_part(world, target_comps, target_desired_part, is_defense)
        
        # ダメージ計算
        damage = calculate_damage(attack_power, success, mobility, defense, is_critical, is_defense)
        
        # 特性に応じた追加効果
        trait_behavior = TraitManager.get_behavior(attack_comp.trait)
        stop_duration = trait_behavior.get_stop_duration(success, mobility)

        return CombatService._create_result_data(True, is_critical, is_defense, damage, hit_part, stop_duration)

    @staticmethod
    def _create_result_data(is_hit, is_critical, is_defense, damage, hit_part, stop_duration) -> CombatResult:
        return CombatResult(
            is_hit=is_hit,
            is_critical=is_critical,
            is_defense=is_defense,
            damage=damage,
            hit_part=hit_part,
            stop_duration=stop_duration
        )

    @staticmethod
    def _get_legs_stats(world, comps) -> Tuple[int, int]:
        """脚部性能（機動・防御）を取得"""
        legs_id = comps['partlist'].parts.get(PartType.LEGS)
        legs_comps = world.try_get_entity(legs_id) if legs_id is not None else None
        
        if legs_comps:
            mob_comp = legs_comps.get('mobility')
            if mob_comp:
                return mob_comp.mobility, mob_comp.defense
        return 0, 0

    @staticmethod
    def _determine_hit_part(world, target_comps, desired_part, is_defense) -> str:
        """実際に命中する部位を決定する"""
        # 生存パーツのリストとマップ
        alive_parts_map = {}
        for pt, pid in target_comps['partlist'].parts.items():
             p_comps = world.try_get_entity(pid)
             if p_comps and p_comps['health'].hp > 0:
                 alive_parts_map[pt] = pid
                 
        alive_keys = list(alive_parts_map.keys())

        if is_defense:
            # 防御成功時は「頭部以外」かつ「HP最大」のパーツがかばう
            non_head = [p for p in alive_keys if p != PartType.HEAD]
            if non_head:
                non_head.sort(
                    key=lambda p: world.entities[alive_parts_map[p]]['health'].hp, 
                    reverse=True
                )
                return non_head[0]
            return PartType.HEAD
        
        else:
            # 防御失敗時は狙った部位へ
            if desired_part and desired_part in alive_keys:
                return desired_part
            elif alive_keys:
                return random.choice(alive_keys)
        
        return PartType.HEAD