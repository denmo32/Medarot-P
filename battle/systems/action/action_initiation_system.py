"""行動開始起案システム"""

from core.ecs import System
from components.action_event import ActionEventComponent
from battle.domain.utils import get_closest_target_by_gauge, reset_gauge_to_cooldown, transition_to_phase
from battle.domain.targeting import TargetingLogic
from battle.constants import GaugeStatus, ActionType, BattlePhase, TraitType, BattleTiming
from battle.service.log_service import LogService
from battle.service.combat_service import CombatService

class ActionInitiationSystem(System):
    """
    1. 行動開始の起案システム
    チャージ完了したエンティティに対し、ターゲットを確定し、事前戦闘計算を行う。
    """
    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        if flow.current_phase != BattlePhase.IDLE or not context.waiting_queue:
            return

        actor_eid = context.waiting_queue[0]
        actor_comps = self.world.try_get_entity(actor_eid)
        if not actor_comps:
            context.waiting_queue.pop(0)
            return

        gauge = actor_comps['gauge']
        if gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0:
            self._initiate_action(actor_eid, actor_comps, gauge, flow, context)

    def _initiate_action(self, actor_eid, actor_comps, gauge, flow, context):
        flow.active_actor_id = actor_eid

        # ターゲットの最終決定
        target_id, target_part = self._resolve_target(actor_eid, actor_comps, gauge)
        
        if gauge.selected_action == ActionType.ATTACK and not target_id:
            self._handle_target_loss(actor_eid, actor_comps, gauge, flow, context)
            return

        # ActionEventエンティティ生成
        event_eid = self.world.create_entity()
        event = ActionEventComponent(
            attacker_id=actor_eid,
            action_type=gauge.selected_action,
            part_type=gauge.selected_part,
            target_id=target_id,
            target_part=target_part
        )
        
        if gauge.selected_action == ActionType.ATTACK:
            event.calculation_result = CombatService.calculate_combat_result(
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

    def _handle_target_loss(self, actor_eid, actor_comps, gauge, flow, context):
        actor_name = actor_comps['medal'].nickname
        context.battle_log.append(LogService.get_target_lost(actor_name))
        transition_to_phase(flow, BattlePhase.LOG_WAIT)
        reset_gauge_to_cooldown(gauge)
        
        if context.waiting_queue and context.waiting_queue[0] == actor_eid:
            context.waiting_queue.pop(0)

    def _resolve_target(self, actor_eid, actor_comps, gauge):
        """アクションタイプと武器特性に応じてターゲットを決定する"""
        if gauge.selected_action != ActionType.ATTACK or not gauge.selected_part:
            return None, None

        part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
        p_comps = self.world.try_get_entity(part_id) if part_id else None
        if not p_comps or 'attack' not in p_comps:
            return None, None

        attack_comp = p_comps['attack']
        if attack_comp.trait in TraitType.MELEE_TRAITS:
            # 格闘：実行時に一番近い敵を狙う
            target_id = get_closest_target_by_gauge(self.world, actor_comps['team'].team_type)
            target_part = TargetingLogic.get_random_alive_part(self.world, target_id) if target_id else None
            return target_id, target_part
        else:
            # 射撃：事前ターゲットを使用
            target_data = gauge.part_targets.get(gauge.selected_part)
            if target_data:
                tid, tpart = target_data
                if TargetingLogic.is_action_target_valid(self.world, tid, tpart):
                    return tid, tpart
        return None, None