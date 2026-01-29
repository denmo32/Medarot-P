"""行動開始起案システム"""

from battle.systems.battle_system_base import BattleSystemBase
from components.action_event_component import ActionEventComponent
from battle.mechanics.flow import transition_to_phase
from domain.constants import GaugeStatus, ActionType
from battle.constants import BattlePhase, BattleTiming
from battle.mechanics.combat import CombatMechanics
from battle.mechanics.action import ActionMechanics
from battle.mechanics.log import LogBuilder

class ActionInitiationSystem(BattleSystemBase):
    def update(self, dt: float):
        context, flow = self.battle_state
        if not context or flow.current_phase != BattlePhase.IDLE or not context.waiting_queue:
            return

        actor_eid = context.waiting_queue[0]
        actor_comps = self.get_comps(actor_eid, 'gauge', 'team', 'partlist')
        if not actor_comps:
            context.waiting_queue.pop(0)
            return

        gauge = actor_comps['gauge']
        if gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0:
            self._handle_initiation(actor_eid, actor_comps, gauge, flow, context)

    def _handle_initiation(self, actor_eid, actor_comps, gauge, flow, context):
        flow.active_actor_id = actor_eid
        
        # ターゲットの解決（特性による動的変更を含む）
        # ActionMechanics が TargetingMechanics と TraitRegistry を統合して判断する
        target_id, target_part = ActionMechanics.resolve_action_target(self.world, actor_eid, actor_comps, gauge)
        
        if gauge.selected_action == ActionType.ATTACK and not target_id:
            actor_name = self.world.try_get_entity(actor_eid)['medal'].nickname
            message = LogBuilder.get_target_lost(actor_name)
            self._interrupt_action(actor_eid, context, flow, message)
            return

        # イベント生成
        event_eid = self.world.create_entity()
        event = ActionEventComponent(
            attacker_id=actor_eid,
            action_type=gauge.selected_action,
            part_type=gauge.selected_part,
            target_id=target_id,
            target_part=target_part
        )
        
        if gauge.selected_action == ActionType.ATTACK:
            event.calculation_result = CombatMechanics.calculate_combat_result(
                self.world, actor_eid, target_id, target_part, gauge.selected_part
            )

        self.world.add_component(event_eid, event)
        flow.processing_event_id = event_eid
        
        # フェーズ遷移
        if gauge.selected_action == ActionType.ATTACK:
            transition_to_phase(flow, BattlePhase.TARGET_INDICATION, BattleTiming.TARGET_INDICATION)
        else:
            transition_to_phase(flow, BattlePhase.EXECUTING)
        
        # キューから削除
        if context.waiting_queue and context.waiting_queue[0] == actor_eid:
            context.waiting_queue.pop(0)

    def _interrupt_action(self, entity_id, context, flow, message: str):
        """アクション中断処理"""
        context.battle_log.append(message)
        transition_to_phase(flow, BattlePhase.LOG_WAIT)
        
        comps = self.world.try_get_entity(entity_id)
        if not comps or 'gauge' not in comps: return

        gauge = comps['gauge']
        current_p = gauge.progress
        gauge.status = GaugeStatus.COOLDOWN
        gauge.progress = max(0.0, 100.0 - current_p)
        gauge.selected_action = None
        gauge.selected_part = None
        
        if entity_id in context.waiting_queue:
            context.waiting_queue.remove(entity_id)