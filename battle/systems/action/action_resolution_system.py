"""行動解決システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.flow import PhaseTransition, FlowMechanics
from battle.mechanics.action import ActionMechanics
from battle.mechanics.action_behavior import ActionBehaviorRegistry, ResolveContext
from battle.mechanics.targeting import TargetingMechanics


class ActionResolutionSystem(BattleSystemBase):
    """
    演出が終了した段階で呼ばれ、ActionEvent 結果を世界に反映する。
    """
    def update(self, dt: float):
        flow = self.flow
        if not flow or flow.current_phase != BattlePhase.EXECUTING:
            return

        event_eid = flow.processing_event_id
        event_comps = self.world.try_get_entity(event_eid) if event_eid is not None else None

        if not event_comps or 'actionevent' not in event_comps:
            FlowMechanics.apply_transition(self.world, PhaseTransition(next_phase=BattlePhase.IDLE))
            return

        event = event_comps['actionevent']
        attacker_comps = self.world.try_get_entity(event.attacker_id)

        if attacker_comps and 'gauge' in attacker_comps:
            behavior = ActionBehaviorRegistry.get(event.action_type)

            attacker_name = attacker_comps['medal'].nickname if attacker_comps and 'medal' in attacker_comps else "Unknown"
            is_actor_part_alive = TargetingMechanics.is_part_alive(self.world, event.attacker_id, event.part_type)

            context = ResolveContext(
                attacker_name=attacker_name,
                is_actor_part_alive=is_actor_part_alive,
                calculation_result=event.calculation_result
            )

            result = behavior.resolve(context)

            # System 内で副作用を適用する
            self._apply_resolution_result(event.attacker_id, result, event_eid)

        # クリーンアップ処理
        if flow.current_phase not in [BattlePhase.CUTIN_RESULT, BattlePhase.LOG_WAIT]:
            if flow.processing_event_id == event_eid:
                flow.processing_event_id = None
            self.world.delete_entity(event_eid)

    def _apply_resolution_result(self, entity_id: int, result, event_id: int):
        context = self.context

        if result.logs and context:
            context.battle_log.extend(result.logs)

        if result.damage_result and event_id is not None:
            event_comps = self.world.try_get_entity(event_id)
            if event_comps and 'actionevent' in event_comps:
                target_id = event_comps['actionevent'].current_target_id
                self.world.add_component(target_id, result.damage_result.to_component())

        if result.gauge_reset:
            comps = self.world.try_get_entity(entity_id)
            if comps and 'gauge' in comps:
                ActionMechanics.apply_gauge_reset(comps['gauge'], result.gauge_reset)

        if result.should_remove_from_queue:
            FlowMechanics.manage_queue(context, entity_id, False)

        FlowMechanics.apply_transition(self.world, PhaseTransition(
            next_phase=result.next_phase, timer=result.phase_timer
        ))
