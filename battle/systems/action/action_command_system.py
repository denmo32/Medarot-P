"""行動コマンド適用システム"""

from battle.systems.base.battle_system_base import BattleSystemBase
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
                atk_comp = self.get_part_component(eid, cmd.part_type, 'attack')
                if atk_comp:
                    c_t, cd_t = calculate_action_times(atk_comp.base_attack)
                    mod = atk_comp.time_modifier
                    gauge.charging_time = c_t * mod
                    gauge.cooldown_time = cd_t * mod

            gauge.status = GaugeStatus.CHARGING
            gauge.progress = 0.0

            context.current_turn_entity_id = None

            # フェーズを IDLE に戻す
            self.apply_transition(PhaseTransition(next_phase=BattlePhase.IDLE))

            if context.waiting_queue and context.waiting_queue[0] == eid:
                self.remove_from_queue(eid)

            self.world.remove_component(eid, 'actioncommand')

