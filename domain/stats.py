"""パーツのステータス計算に関するドメインロジック"""

from typing import Dict, Any
from domain.attribute import AttributeLogic
from battle.mechanics.skill import SkillRegistry

class StatsLogic:
    """パーツ生成時やステータス更新時の計算ロジックを統合する"""

    @staticmethod
    def calculate_initial_stats(data: Dict[str, Any], part_type: str, medal_attr: str) -> Dict[str, Any]:
        """パーツデータとメダル属性に基づいて、最終的なステータス辞書を構築する"""
        trait = data.get("trait")
        skill = data.get("skill")
        
        skill_behavior = SkillRegistry.get(skill)
        time_modifier = skill_behavior.get_time_modifier()

        stats = {
            "hp": data.get("hp", 0),
            "attack": data.get("attack"), 
            "base_attack": data.get("attack"),
            "success": data.get("success", 0),
            "mobility": data.get("mobility", 0),
            "defense": data.get("defense", 0),
            "trait": trait,
            "skill": skill,
            "attribute": data.get("attribute", "undefined"),
            "time_modifier": time_modifier
        }
        
        AttributeLogic.apply_passive_stats_bonus(stats, part_type, medal_attr)
                    
        return stats