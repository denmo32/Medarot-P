"""行動解決システム"""

from core.ecs import System
from components.battle import DamageEventComponent
from battle.constants import ActionType, BattlePhase
from battle.domain.utils import transition_to_phase, get_battle_state
from battle.service.log_service import LogService
from battle.service.action_service import ActionService

class ActionResolutionSystem(System):
    """
    2. 行動解決システム
    事前に計算された ActionEvent の結果に基づき、DamageEventを発行する。
    """
    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not flow or flow.current_phase != BattlePhase.EXECUTING:
            return
        
        event_eid = flow.processing_event_id
        event_comps = self.world.try_get_entity(event_eid) if event_eid is not None else None
        
        if not event_comps or 'actionevent' not in event_comps:
            transition_to_phase(flow, BattlePhase.IDLE)
            return

        event = event_comps['actionevent']
        self._resolve_action(event, context, flow)
        
        if flow.current_phase != BattlePhase.CUTIN_RESULT:
            self.world.delete_entity(event_eid)
            flow.processing_event_id = None

    def _resolve_action(self, event, context, flow):
        attacker_id = event.attacker_id
        attacker_comps = self.world.try_get_entity(attacker_id)
        if not attacker_comps: return

        if event.action_type == ActionType.ATTACK:
            self._handle_attack_action(event, attacker_comps, context)
            transition_to_phase(flow, BattlePhase.CUTIN_RESULT)
        elif event.action_type == ActionType.SKIP:
            context.battle_log.append(LogService.get_skip_action(attacker_comps['medal'].nickname))
            transition_to_phase(flow, BattlePhase.LOG_WAIT)

        if 'gauge' in attacker_comps:
            ActionService.reset_to_cooldown(attacker_comps['gauge'])

    def _handle_attack_action(self, event, attacker_comps, context):
        attacker_name = attacker_comps['medal'].nickname
        part_id = attacker_comps['partlist'].parts.get(event.part_type)
        part_comps = self.world.try_get_entity(part_id) if part_id is not None else None
        
        if not part_comps or part_comps['health'].hp <= 0:
            context.battle_log.append(LogService.get_part_broken_attack(attacker_name))
            return

        res = event.calculation_result
        if res is None:
            context.battle_log.append(LogService.get_target_lost(attacker_name))
            return

        if not res.is_hit:
            return
            
        self.world.add_component(event.current_target_id, DamageEventComponent(
            attacker_id=event.attacker_id,
            attacker_part=event.part_type,
            damage=res.damage,
            target_part=res.hit_part,
            is_critical=res.is_critical,
            stop_duration=res.stop_duration
        ))