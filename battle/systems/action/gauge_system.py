"""ATBゲージ更新システム"""

from core.ecs import System
from battle.constants import GaugeStatus, BattlePhase, ActionType
from battle.domain.utils import interrupt_gauge_return_home, transition_to_phase
from battle.domain.targeting import TargetingLogic
from battle.service.log_service import LogService

class GaugeSystem(System):
    """ATBゲージの進行管理、およびチャージ中のアクション有効性監視を担当"""
    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        if flow.current_phase != BattlePhase.IDLE:
            return

        gauge_entities = self.world.get_entities_with_components('gauge', 'defeated', 'medal', 'partlist')

        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            if comps['gauge'].status == GaugeStatus.CHARGING:
                self._check_interruption(eid, comps, comps['gauge'], context, flow)

        if flow.current_phase == BattlePhase.LOG_WAIT:
            return

        self._update_waiting_queue(gauge_entities, context)

        if context.waiting_queue:
            return

        self._advance_gauges(gauge_entities, dt)

    def _check_interruption(self, eid, comps, gauge, context, flow):
        """チャージ中の継続条件をチェックし、満たさない場合は中断させる"""
        actor_name = comps['medal'].nickname
        
        # 1. 自身の予約パーツが破壊されたか
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            if not TargetingLogic.is_action_target_valid(self.world, eid, gauge.selected_part):
                message = LogService.get_part_broken_interruption(actor_name)
                self._interrupt(eid, gauge, context, flow, message)
                return

        # 2. ターゲットがロストしたか（事前ターゲットの場合のみ）
        target_data = gauge.part_targets.get(gauge.selected_part)
        if target_data:
            target_id, target_part_type = target_data
            if not TargetingLogic.is_action_target_valid(self.world, target_id, target_part_type):
                message = LogService.get_target_lost(actor_name)
                self._interrupt(eid, gauge, context, flow, message)
                return

    def _interrupt(self, eid, gauge, context, flow, message):
        """アクションを中断し、その地点からホームへ戻る"""
        context.battle_log.append(message)
        transition_to_phase(flow, BattlePhase.LOG_WAIT)
        interrupt_gauge_return_home(gauge)
        
        if eid in context.waiting_queue:
            context.waiting_queue.remove(eid)

    def _update_waiting_queue(self, gauge_entities, context):
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            if comps['gauge'].status == GaugeStatus.ACTION_CHOICE:
                if eid not in context.waiting_queue:
                    context.waiting_queue.append(eid)

    def _advance_gauges(self, gauge_entities, dt):
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            gauge = comps['gauge']
            
            if gauge.stop_timer > 0:
                gauge.stop_timer = max(0.0, gauge.stop_timer - dt)
                continue
            
            if gauge.status == GaugeStatus.CHARGING:
                gauge.progress += dt / gauge.charging_time * 100.0
                if gauge.progress >= 100.0:
                    gauge.progress = 100.0
                    if eid not in self.world.entities[0]['battlecontext'].waiting_queue:
                        self.world.entities[0]['battlecontext'].waiting_queue.append(eid)
            
            elif gauge.status == GaugeStatus.COOLDOWN:
                gauge.progress += dt / gauge.cooldown_time * 100.0
                if gauge.progress >= 100.0:
                    gauge.progress = 0.0
                    gauge.status = GaugeStatus.ACTION_CHOICE
                    gauge.part_targets = {} 
                    gauge.selected_action = None
                    gauge.selected_part = None
                    if eid not in self.world.entities[0]['battlecontext'].waiting_queue:
                        self.world.entities[0]['battlecontext'].waiting_queue.append(eid)