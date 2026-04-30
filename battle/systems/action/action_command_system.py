"""行動コマンド適用システム"""

from battle.systems.battle_system_base import BattleSystemBase
from domain.constants import ActionType, GaugeStatus
from battle.constants import BattlePhase
from domain.gauge_logic import calculate_action_times
from domain.flow_logic import PhaseTransition


class ActionCommandSystem(BattleSystemBase):
    """プレイヤー/エネミーの行動コマンドをゲージに適用"""

    def update(self, dt: float):
        context = self.context
        flow = self.flow

        if not context or not flow:
            return

        for eid, comps in self.world.get_entities_with_components('actioncommand', 'gauge', 'partlist'):
            cmd = comps['actioncommand']
            gauge = comps['gauge']
            part_list = comps['partlist']

            gauge.selected_action = cmd.action_type
            gauge.selected_part = cmd.part_type

            if cmd.action_type == ActionType.ATTACK and cmd.part_type:
                part_id = part_list.parts.get(cmd.part_type)
                p_comps = self.world.try_get_entity(part_id)
                if p_comps and 'attack' in p_comps:
                    atk_comp = p_comps['attack']
                    c_t, cd_t = calculate_action_times(atk_comp.base_attack)
                    mod = atk_comp.time_modifier
                    gauge.charging_time = c_t * mod
                    gauge.cooldown_time = cd_t * mod

            gauge.status = GaugeStatus.CHARGING
            gauge.progress = 0.0

            context.current_turn_entity_id = None

            # フェーズを IDLE に戻す
            self._apply_transition(PhaseTransition(next_phase=BattlePhase.IDLE))

            if context.waiting_queue and context.waiting_queue[0] == eid:
                context.waiting_queue.pop(0)

            self.world.remove_component(eid, 'actioncommand')

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

