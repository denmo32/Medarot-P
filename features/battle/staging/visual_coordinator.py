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
        self.cutin: Optional[CutinDirector] = None
        self.radar_director: Optional[TargetRadarDirector] = None

    @property
    def cutin_director(self) -> Optional[CutinDirector]:
        return self.cutin

    def is_combat_active(self, robot: 'Robot') -> bool:
        """カットイン戦闘の当事者としてアクティブ表示すべきか"""
        return self.cutin is not None and self.cutin.is_combatant(robot)

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

    def stage_pierce_damage(self, report: 'ExecutionReport'):
        """貫通ダメージの目標HPを反映する"""
        if not report.target or not report.result:
            return
        target_vs = self.visual_states.get(report.target)
        pierce = report.result.pierce_effect
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
        self.cutin = CutinDirector(actor=actor, target=target, part=part, report=report)
        return self.cutin

    def update_cutin(self, dt: float):
        if self.cutin:
            self.cutin.update(dt)

    def advance_cutin(self):
        if self.cutin:
            self.cutin.advance()

    def clear_cutin(self):
        self.cutin = None

    # === ターゲットレーダー演出のライフサイクル ===

    def start_radar(self, attacker_index: int, target_index: int) -> TargetRadarDirector:
        self.radar_director = TargetRadarDirector(attacker_index, target_index)
        return self.radar_director

    def clear_radar(self):
        self.radar_director = None