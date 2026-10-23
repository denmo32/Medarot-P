"""バトルの演出進行（HPアニメーション、カットイン、レーダー）を一元管理するコーディネーター。"""
from typing import Dict, Optional, Sequence, TYPE_CHECKING

from .cutin_director import CutinDirector
from .target_radar_director import TargetRadarDirector
from .visual_state import RobotVisualState

if TYPE_CHECKING:
    from ..entities.commands import ExecutionReport
    from ..entities.part import Part
    from ..entities.robot import Robot


class VisualCoordinator:
    """戦闘の視覚演出（HP変動アニメーション・カットイン・レーダー）を一元管理する。"""

    def __init__(self, robots: Sequence['Robot']):
        self.visual_states: Dict['Robot', RobotVisualState] = {
            r: RobotVisualState(r) for r in robots
        }
        self.cutin_director: Optional[CutinDirector] = None
        self.radar_director: Optional[TargetRadarDirector] = None

        self.active_actor: Optional['Robot'] = None
        self.active_target: Optional['Robot'] = None
        self.active_report: Optional['ExecutionReport'] = None

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

    def stage_primary_damage(self, report: 'ExecutionReport'):
        """主攻撃のダメージ目標HPを反映する"""
        if not report.target or not report.result or not report.result.success:
            return
        target_vs = self.visual_states.get(report.target)
        primary = report.result.primary_damage
        if target_vs and primary and primary.effective_damage > 0:
            target_vs.apply_damage_target(primary.part_type, primary.effective_damage)

    def stage_pierce_damage(self, target: 'Robot', report: 'ExecutionReport'):
        """貫通ダメージの目標HPを反映する"""
        target_vs = self.visual_states.get(target)
        pierce = report.result.pierce_effect if report.result else None
        if target_vs and pierce and pierce.effective_damage > 0:
            target_vs.apply_damage_target(pierce.part_type, pierce.effective_damage)

    def sync_all_targets(self):
        for vs in self.visual_states.values():
            vs.sync_all_targets()

    # === カットイン演出のライフサイクル ===

    def start_cutin(
        self,
        actor: 'Robot',
        target: 'Robot',
        part: Optional['Part'],
        report: 'ExecutionReport',
    ) -> CutinDirector:
        self.active_actor = actor
        self.active_target = target
        self.active_report = report
        self.cutin_director = CutinDirector.create(part=part, result=report.result)
        return self.cutin_director

    def update_cutin(self, dt: float):
        if self.cutin_director:
            self.cutin_director.update(dt)

    def advance_cutin(self):
        if self.cutin_director:
            self.cutin_director.advance()

    def update_cutin_report(self, report: 'ExecutionReport'):
        self.active_report = report
        if self.cutin_director and report.result:
            self.cutin_director.show_result()
            self.cutin_director.update_final_result(report.result)

    def clear_cutin(self):
        self.cutin_director = None
        self.active_actor = None
        self.active_target = None
        self.active_report = None

    # === ターゲットレーダー演出のライフサイクル ===

    def start_radar(self, attacker_index: int, target_index: int) -> TargetRadarDirector:
        self.radar_director = TargetRadarDirector(attacker_index, target_index)
        return self.radar_director

    def clear_radar(self):
        self.radar_director = None