"""戦闘計算サービス"""

import random
from typing import Dict, Any, List, Optional
from battle.constants import PartType
from battle.attributes import AttributeLogic
from battle.traits import TraitManager
from battle.calculator import (
    calculate_hit_probability,
    calculate_break_probability,
    check_is_hit,
    check_attack_outcome,
    calculate_damage
)

class CombatService:
    """
    戦闘結果（命中、ダメージ、部位決定など）を計算するドメインサービス。
    ECSのWorldやEntityには依存せず、渡されたパラメータに基づいて計算を行う。
    """

    @staticmethod
    def calculate_combat_result(
        attacker_data: Dict[str, Any],
        target_data: Dict[str, Any],
        target_alive_parts_map: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        戦闘の事前計算を行うメインメソッド。

        Args:
            attacker_data: {
                'medal_attr': str,
                'part_attr': str,
                'attack_val': int,
                'success_val': int,
                'trait': str
            }
            target_data: {
                'medal_attr': str,
                'mobility': int,
                'defense': int,
                'desired_part': str (攻撃側が狙った部位)
            }
            target_alive_parts_map: {part_type: hp} の辞書（生存パーツのみ）

        Returns:
            Dict: ActionEventに格納する計算結果
        """
        
        # 1. 属性相性補正の計算
        atk_bonus, def_bonus = AttributeLogic.calculate_affinity_bonus(
            attacker_data['medal_attr'],
            attacker_data['part_attr'],
            target_data['medal_attr']
        )

        # 2. ステータス補正適用 (最小値クリップ含む)
        adjusted_success = max(1, attacker_data['success_val'] + atk_bonus)
        adjusted_attack = max(1, attacker_data['attack_val'] + atk_bonus)
        
        adjusted_mobility = max(0, target_data['mobility'] + def_bonus)
        adjusted_defense = max(0, target_data['defense'] + def_bonus)

        # 3. 命中判定
        hit_prob = calculate_hit_probability(adjusted_success, adjusted_mobility)
        
        if not check_is_hit(hit_prob):
            return CombatService._create_result_data(False, False, False, 0, None, 0.0)

        # 4. 命中時の詳細計算（クリティカル・防御）
        break_prob = calculate_break_probability(adjusted_success, adjusted_defense)
        is_critical, is_defense = check_attack_outcome(hit_prob, break_prob)
        
        # 5. 命中部位の決定
        hit_part = CombatService._determine_hit_part(
            target_data['desired_part'],
            is_defense,
            target_alive_parts_map
        )
        
        # 6. ダメージ計算
        damage = calculate_damage(
            adjusted_attack, adjusted_success, 
            adjusted_mobility, adjusted_defense, 
            is_critical, is_defense
        )
        
        # 7. 特性による追加効果
        trait_behavior = TraitManager.get_behavior(attacker_data['trait'])
        stop_duration = trait_behavior.get_stop_duration(adjusted_success, adjusted_mobility)

        return CombatService._create_result_data(True, is_critical, is_defense, damage, hit_part, stop_duration)

    @staticmethod
    def _determine_hit_part(desired_part: str, is_defense: bool, alive_parts_map: Dict[str, int]) -> str:
        """実際に命中する部位を決定する"""
        alive_keys = list(alive_parts_map.keys())
        if not alive_keys:
            # 万が一全て破壊されている場合（通常ありえないがフォールバック）
            return PartType.HEAD

        if is_defense:
            # 防御成功時は「頭部以外」かつ「HP最大」のパーツがかばう
            non_head = [p for p in alive_keys if p != PartType.HEAD]
            if non_head:
                # HPが高い順にソート
                non_head.sort(key=lambda p: alive_parts_map[p], reverse=True)
                return non_head[0]
            # 頭しか残っていない場合は頭に当たる
            return PartType.HEAD
        
        else:
            # 防御失敗（通常命中）時
            if desired_part and desired_part in alive_keys:
                return desired_part
            elif alive_keys:
                # 狙った部位がない場合はランダム
                return random.choice(alive_keys)
        
        return PartType.HEAD

    @staticmethod
    def _create_result_data(is_hit, is_critical, is_defense, damage, hit_part, stop_duration):
        return {
            'is_hit': is_hit,
            'is_critical': is_critical,
            'is_defense': is_defense,
            'damage': damage,
            'hit_part': hit_part,
            'stop_duration': stop_duration
        }