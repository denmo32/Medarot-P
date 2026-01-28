"""行動開始起案システム"""

from core.ecs import System
from components.action_event_component import ActionEventComponent
from battle.mechanics.flow import transition_to_phase, get_battle_state
from battle.mechanics.targeting import TargetingMechanics
from domain.constants import GaugeStatus, ActionType
from battle.constants import BattlePhase, BattleTiming
from battle.mechanics.combat import CombatMechanics
from battle.mechanics.action import ActionMechanics

class ActionInitiationSystem(System):
    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not context or flow.current_phase != BattlePhase.IDLE or not context.waiting_queue:
            return

        actor_eid = context.waiting_queue[0]
        actor_comps = self.world.try_get_entity(actor_eid)
        if not actor_comps:
            context.waiting_queue.pop(0)
            return

        gauge = actor_comps['gauge']
        if gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0:
            self._handle_initiation(actor_eid, actor_comps, gauge, flow, context)

    def _handle_initiation(self, actor_eid, actor_comps, gauge, flow, context):
        flow.active_actor_id = actor_eid
        target_id, target_part = TargetingMechanics.resolve_action_target(self.world, actor_eid, actor_comps, gauge)
        
        if gauge.selected_action == ActionType.ATTACK and not target_id:
            ActionMechanics.handle_target_loss(self.world, actor_eid, context, flow)
            return

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
        
        if gauge.selected_action == ActionType.ATTACK:
            transition_to_phase(flow, BattlePhase.TARGET_INDICATION, BattleTiming.TARGET_INDICATION)
        else:
            transition_to_phase(flow, BattlePhase.EXECUTING)
        
        if context.waiting_queue and context.waiting_queue[0] == actor_eid:
            context.waiting_queue.pop(0)