"""アクション中断監視システム"""

from core.ecs import System
from battle.constants import BattlePhase, ActionType
from battle.service.flow_service import get_battle_state
from battle.logic.targeting import TargetingService
from battle.service.log_service import LogService
from battle.service.action_service import ActionService
from domain.constants import GaugeStatus

class InterruptionSystem(System):
    """チャージ中のエンティティに対し、継続条件（パーツ生存、ターゲット生存）を監視する。"""

    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not context or not flow:
            return

        # IDLE状態の時のみ中断判定を行う（演出中は状態が固定されるため）
        if flow.current_phase != BattlePhase.IDLE:
            return

        gauge_entities = self.world.get_entities_with_components('gauge', 'defeated', 'medal', 'partlist')

        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated:
                continue
            
            gauge = comps['gauge']
            if gauge.status == GaugeStatus.CHARGING:
                self._check_interruption(eid, comps, gauge, context, flow)

    def _check_interruption(self, eid, comps, gauge, context, flow):
        """チャージ中の継続条件をチェックし、満たさない場合は中断させる"""
        actor_name = comps['medal'].nickname
        
        # 1. 予約パーツ自身の破壊チェック
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            if not TargetingService.is_action_target_valid(self.world, eid, gauge.selected_part):
                message = LogService.get_part_broken_interruption(actor_name)
                ActionService.interrupt_action(self.world, eid, context, flow, message)
                return

        # 2. ターゲットロストチェック（射撃などの事前ターゲット）
        target_data = gauge.part_targets.get(gauge.selected_part)
        if target_data:
            target_id, target_part_type = target_data
            if not TargetingService.is_action_target_valid(self.world, target_id, target_part_type):
                message = LogService.get_target_lost(actor_name)
                ActionService.interrupt_action(self.world, eid, context, flow, message)
                return