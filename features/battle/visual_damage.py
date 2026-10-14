"""戦闘結果から視覚的なダメージ演出ステップを構築するヘルパー。"""
from typing import Dict, List, TYPE_CHECKING
from domain.constants import PartType

if TYPE_CHECKING:
    from features.battle.commands import ExecutionReport


def build_damage_visual_steps(report: 'ExecutionReport') -> List[Dict[PartType, float]]:
    """ExecutionReport から視覚演出（多段階HP変動など）のステップリストを生成する純粋関数。"""
    if not report.target or not report.result or not report.result.success:
        return []

    steps: List[Dict[PartType, float]] = []
    hit_part = report.result.hit_part
    if hit_part:
        steps.append({hit_part: float(report.target.get_part_hp(hit_part))})

    pierce = report.pierce_effect
    if pierce:
        steps.append({pierce.part_type: float(report.target.get_part_hp(pierce.part_type))})

    return steps