"""行動解決システム"""

from battle.systems.base.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from domain.flow_logic import PhaseTransition
from domain.action_logic import get_action_behavior, ResolveContext
from components.battle_component import DamageEventComponent


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
            self.apply_transition(PhaseTransition(next_phase=BattlePhase.IDLE))
            return

        event = event_comps['actionevent']
        attacker_comps = self.world.try_get_entity(event.attacker_id)

        if attacker_comps and 'gauge' in attacker_comps:
            behavior = get_action_behavior(event.action_type)

            attacker_name = attacker_comps['medal'].nickname if attacker_comps and 'medal' in attacker_comps else "Unknown"
            is_actor_part_alive = self.is_part_alive(event.attacker_id, event.part_type)

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

        if result.calculation_result and result.calculation_result.is_hit and event_id is not None:
            event_comps = self.world.try_get_entity(event_id)
            if event_comps and 'actionevent' in event_comps:
                event = event_comps['actionevent']
                target_id = event.target_id
                
                # CombatResult から DamageEventComponent を生成
                c_res = result.calculation_result
                damage_event = DamageEventComponent(
                    attacker_id=event.attacker_id,
                    attacker_part=event.part_type,
                    damage=c_res.damage,
                    target_part=c_res.hit_part if c_res.hit_part else "",
                    is_critical=c_res.is_critical,
                    added_effects=c_res.added_effects
                )
                self.world.add_component(target_id, damage_event)

        if result.gauge_reset:
            comps = self.world.try_get_entity(entity_id)
            if comps and 'gauge' in comps:
                self.apply_gauge_reset(comps['gauge'], result.gauge_reset)

        if result.should_remove_from_queue:
            self.remove_from_queue(entity_id)

        self.apply_transition(PhaseTransition(
            next_phase=result.next_phase, timer=result.phase_timer
        ))

