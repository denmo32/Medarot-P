"""行動解決システム"""

from battle.systems.battle_system_base import BattleSystemBase
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
            self._apply_transition(PhaseTransition(next_phase=BattlePhase.IDLE))
            return

        event = event_comps['actionevent']
        attacker_comps = self.world.try_get_entity(event.attacker_id)

        if attacker_comps and 'gauge' in attacker_comps:
            behavior = get_action_behavior(event.action_type)

            attacker_name = attacker_comps['medal'].nickname if attacker_comps and 'medal' in attacker_comps else "Unknown"
            is_actor_part_alive = self._is_part_alive(event.attacker_id, event.part_type)

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
                self._apply_gauge_reset(comps['gauge'], result.gauge_reset)

        if result.should_remove_from_queue:
            self._remove_from_queue(entity_id)

        self._apply_transition(PhaseTransition(
            next_phase=result.next_phase, timer=result.phase_timer
        ))

    # --- Local Helpers ---

    def _apply_transition(self, transition: PhaseTransition):
        flow = self.flow
        ctx = self.context
        if not flow: return
        flow.current_phase = transition.next_phase
        flow.phase_timer = transition.timer
        if transition.actor_id is not None: flow.active_actor_id = transition.actor_id
        if transition.event_id is not None: flow.processing_event_id = transition.event_id
        if transition.logs and ctx: ctx.battle_log.extend(transition.logs)
        if transition.next_phase == BattlePhase.IDLE:
            flow.processing_event_id = None
            flow.active_actor_id = None

    def _remove_from_queue(self, eid: int):
        if self.context and eid in self.context.waiting_queue:
            self.context.waiting_queue.remove(eid)

    def _is_part_alive(self, eid: int, part_type: str) -> bool:
        comps = self.world.try_get_entity(eid)
        if not comps or (comps.get('defeated') and comps['defeated'].is_defeated): return False
        pid = comps['partlist'].parts.get(part_type)
        if pid is None: return False
        p_comps = self.world.try_get_entity(pid)
        return bool(p_comps and 'health' in p_comps and p_comps['health'].hp > 0)

    def _apply_gauge_reset(self, gauge, reset_data):
        gauge.status = reset_data.status
        gauge.progress = reset_data.progress
        if reset_data.clear_selection:
            gauge.selected_action = None
            gauge.selected_part = None
            gauge.part_targets = {}

