"""戦闘計算システム"""

from typing import Optional, Dict
from battle.systems.base.battle_system_base import BattleSystemBase
from domain.constants import ActionType
from domain.combat_logic import (
    calculate_adjusted_stats, get_defensive_penalty, calculate_combat_result,
    MedalParams, AttackParams
)


class CombatCalculationSystem(BattleSystemBase):
    """
    ActionEvent を監視し、攻撃アクションの場合に戦闘計算を実行して結果を付与する。
    """
    def update(self, dt: float):
        # 計算未完了の ActionEvent を探す
        for event_eid, comps in self.world.get_entities_with_components('actionevent'):
            event = comps['actionevent']
            
            if event.action_type == ActionType.ATTACK and event.calculation_result is None:
                # 戦闘計算を実行
                result = self._calculate_combat(
                    event.attacker_id, 
                    event.part_type, 
                    event.target_id, 
                    event.target_part
                )
                event.calculation_result = result

    def _calculate_combat(
        self,
        actor_eid: int,
        attacker_part_type: str,
        target_id: int,
        target_desired_part: Optional[str]
    ):
        """戦闘計算を実行する"""
        world = self.world
        a_comps = world.try_get_entity(actor_eid)
        t_comps = world.try_get_entity(target_id)
        
        if not a_comps or not t_comps:
            return None
            
        # 攻撃側メダル
        attacker_medal = MedalParams(attribute=a_comps['medal'].attribute)
        
        # 攻撃パーツ
        part_id = a_comps['partlist'].parts.get(attacker_part_type)
        if not part_id: return None
        p_comps = world.try_get_entity(part_id)
        if not p_comps or 'attack' not in p_comps: return None
        
        attacker_part = AttackParams(
            success=p_comps['attack'].success,
            attack=p_comps['attack'].attack,
            part_attribute=p_comps['part'].attribute,
            skill_type=p_comps['attack'].skill_type,
            trait=p_comps['attack'].trait
        )
        
        # 攻撃側脚部
        attacker_legs = self.get_legs_stats(actor_eid)
        
        # 防御側メダル
        target_medal = MedalParams(attribute=t_comps['medal'].attribute)
        
        # 防御側脚部
        target_legs = self.get_legs_stats(target_id)
        
        # 防御側ゲージペナルティ情報
        t_gauge = t_comps.get('gauge')
        t_status = t_gauge.status if t_gauge else ""
        t_sel_part = t_gauge.selected_part if t_gauge else None
        t_skill_type = None
        if t_sel_part:
            tp_id = t_comps['partlist'].parts.get(t_sel_part)
            if tp_id:
                tp_comps = world.try_get_entity(tp_id)
                if tp_comps and 'attack' in tp_comps:
                    t_skill_type = tp_comps['attack'].skill_type

        # 生存パーツ HP
        target_part_hps = self.get_alive_parts_hp(target_id)

        # 2. 戦闘計算実行
        stats = calculate_adjusted_stats(
            attacker_medal=attacker_medal,
            attacker_part=attacker_part,
            attacker_legs=attacker_legs,
            target_medal=target_medal,
            target_legs=target_legs
        )
        
        penalty = get_defensive_penalty(
            target_gauge_status=t_status,
            target_selected_part=t_sel_part,
            target_part_skill_type=t_skill_type
        )
        
        return calculate_combat_result(
            stats=stats,
            penalty=penalty,
            trait_name=attacker_part.trait,
            target_part_hps=target_part_hps,
            target_desired_part=target_desired_part
        )
