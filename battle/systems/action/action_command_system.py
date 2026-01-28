"""行動コマンド適用システム"""

from core.ecs import System
from domain.constants import ActionType, GaugeStatus
from battle.constants import BattlePhase
from domain.gauge_logic import calculate_action_times
from battle.mechanics.flow import transition_to_phase, get_battle_state

class ActionCommandSystem(System):
    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not context or not flow: return

        for eid, comps in self.world.get_entities_with_components('actioncommand', 'gauge', 'partlist'):
            cmd = comps['actioncommand']
            gauge = comps['gauge']
            part_list = comps['partlist']

            gauge.selected_action = cmd.action_type
            gauge.selected_part = cmd.part_type

            if cmd.action_type == ActionType.ATTACK and cmd.part_type:
                part_id = part_list.parts.get(cmd.part_type)
                if part_id is not None:
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
            transition_to_phase(flow, BattlePhase.IDLE)
            
            if context.waiting_queue and context.waiting_queue[0] == eid:
                context.waiting_queue.pop(0)

            self.world.remove_component(eid, 'actioncommand')