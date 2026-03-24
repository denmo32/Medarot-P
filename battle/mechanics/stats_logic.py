"""パーツのステータス計算に関するドメインロジック"""

from typing import Dict, Any
from domain.models import PartData
from domain.attribute import AttributeLogic
from battle.mechanics.skill import SkillRegistry


class StatsLogic:
    """パーツ生成時やステータス更新時の計算ロジックを統合する"""

    @staticmethod
    def calculate_initial_stats(data: PartData, part_type: str, medal_attr: str) -> Dict[str, Any]:
        """パーツデータとメダル属性に基づいて、最終的なステータス辞書を構築する"""
        trait = data.trait
        skill = data.skill

        skill_behavior = SkillRegistry.get(skill)
        time_modifier = skill_behavior.get_time_modifier()

        base_stats = {
            "hp": data.hp,
            "attack": data.attack,
            "base_attack": data.attack,
            "success": data.success,
            "mobility": data.mobility,
            "defense": data.defense,
            "trait": trait,
            "skill": skill,
            "attribute": data.attribute,
            "time_modifier": time_modifier
        }

        # パッシブボーナスを適用した新しい Stats を取得
        stats = AttributeLogic.apply_passive_stats_bonus(base_stats, part_type, medal_attr)

        return stats
