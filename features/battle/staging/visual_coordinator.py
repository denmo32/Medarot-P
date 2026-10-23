"""バトルの演出進行（HPアニメーション、カットイン、レーダー）を一元管理するコーディネーター。"""
from typing import Dict, List, Optional, Sequence, TYPE_CHECKING

from domain.constants import PartType
from .cutin_director import CutinDirector
from .target_radar_director import TargetRadarDirector
from .visual_state import RobotVisualState

if TYPE_CHECKING:
    from domain.models import ActionResult
    from ..entities.commands import ExecutionReport
    from ..entities.part import Part
    from ..entities.robot import Robot


def _build_damage_visual_steps(report: 'ExecutionReport') -> List[Dict[PartType, float]]:
    """ExecutionReport から視覚演出（多段階HP変動など）のステップリストを生成する純粋関数"""
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


class VisualCoordinator:
    """戦闘の視覚演出（HP変動アニメーション・カットイン・レーダー）を一元管理する。"""

    def __init__(self, robots: Sequence['Robot']):
        self.visual_states: Dict['Robot', RobotVisualState] = {
            r: RobotVisualState(r) for r in robots
        }
        self.cutin_director: Optional[CutinDirector] = None
        self.radar_director: Optional[TargetRadarDirector] = None

    # === HP アニメーション判定 ===

    def is_hp_animating(self) -> bool:
        return any(vs.is_hp_animating for vs in self.visual_states.values())

    # === フレーム更新 ===

    def update(self, dt: float):
        for vs in self.visual_states.values():
            vs.update(dt)

        if self.radar_director:
            self.radar_director.update(dt)

    # === ダメージ演出のステージング ===

    def stage_damage(self, report: 'ExecutionReport'):
        if report and report.target:
            steps = _build_damage_visual_steps(report)
            if steps:
                self.visual_states[report.target].stage_damage_steps(steps)

    def advance_damage_step(self, target: 'Robot'):
        if target in self.visual_states:
            self.visual_states[target].advance_damage_step()

    def sync_all_targets(self):
        for vs in self.visual_states.values():
            vs.sync_all_targets()

    # === カットイン演出のライフサイクル ===

    def start_cutin(self, part: Optional['Part'], report: 'ExecutionReport') -> CutinDirector:
        result = report.result
        has_pierce = report.has_pierce
        self.cutin_director = CutinDirector.create(part=part, result=result, has_pierce=has_pierce)
        return self.cutin_director

    def update_cutin(self, dt: float):
        if self.cutin_director:
            self.cutin_director.update(dt)

    def advance_cutin(self):
        if self.cutin_director:
            self.cutin_director.advance()

    def update_cutin_result(self, result: 'ActionResult'):
        if self.cutin_director:
            self.cutin_director.show_result()
            self.cutin_director.update_final_result(result)

    def clear_cutin(self):
        self.cutin_director = None

    # === ターゲットレーダー演出のライフサイクル ===

    def start_radar(self, attacker_index: int, target_index: int) -> TargetRadarDirector:
        self.radar_director = TargetRadarDirector(attacker_index, target_index)
        return self.radar_director

    def clear_radar(self):
        self.radar_director = None