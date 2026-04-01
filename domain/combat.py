"""戦闘ステータス生成ロジック（ドメイン層）"""

from typing import Dict, Any
from domain.models import PartData, MedalData
from domain.attribute import AttributeLogic
from battle.mechanics.skill import SkillRegistry


class CombatDomain:
    """
    ドメイン層：戦闘ステータス生成
    
    責務：PartData と MedalData から、戦闘で実際に使われるステータスを生成する。
    Factory や ECS の知識は持たない純粋なドメインロジック。
    """

    @staticmethod
    def create_battle_stats(part_data: PartData, medal_data: MedalData, part_type: str) -> Dict[str, Any]:
        """
        パーツデータとメダル属性に基づいて、最終的な戦闘ステータス辞書を構築する。
        
        Args:
            part_data: パーツのデータ
            medal_data: メダルのデータ
            part_type: パーツタイプ（"head", "right_arm", "left_arm", "legs"）
            
        Returns:
            戦闘ステータス辞書（hp, attack, success, mobility, defense, attribute, time_modifier, skill, trait, base_attack）
        """
        trait = part_data.trait
        skill = part_data.skill

        skill_behavior = SkillRegistry.get(skill)
        time_modifier = skill_behavior.get_time_modifier()

        # 基本ステータス
        base_stats = {
            "hp": part_data.hp,
            "attack": part_data.attack,
            "base_attack": part_data.attack,
            "success": part_data.success,
            "mobility": part_data.mobility,
            "defense": part_data.defense,
            "trait": trait,
            "skill": skill,
            "attribute": part_data.attribute,
            "time_modifier": time_modifier
        }

        # メダル属性との相性によるパッシブボーナスを適用
        stats = AttributeLogic.apply_passive_stats_bonus(
            base_stats, 
            part_type, 
            medal_data.attribute
        )

        return stats
