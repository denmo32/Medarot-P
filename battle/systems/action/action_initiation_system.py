"""行動開始起案システム"""

import random
from core.ecs import System
from components.action_event import ActionEventComponent
from battle.domain.utils import get_closest_target_by_gauge, reset_gauge_to_cooldown, is_target_valid
from battle.constants import GaugeStatus, ActionType, BattlePhase, TraitType, PartType, BattleTiming
from battle.service.log_service import LogService
from battle.service.combat_service import CombatService

class ActionInitiationSystem(System):
    """
    1. 行動開始の起案システム
    チャージ完了したエンティティに対し、ターゲットを確定し、
    CombatServiceを利用して事前に戦闘計算を行った上で ActionEvent を生成する。
    """
    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        # IDLEフェーズかつ待機列がある場合のみ処理
        if flow.current_phase != BattlePhase.IDLE or not context.waiting_queue:
            return

        actor_eid = context.waiting_queue[0]
        actor_comps = self.world.try_get_entity(actor_eid)
        if not actor_comps:
            context.waiting_queue.pop(0)
            return

        gauge = actor_comps['gauge']
        
        # チャージ完了（100%）しているか確認
        if gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0:
            self._initiate_action(actor_eid, actor_comps, gauge, flow, context)

    def _initiate_action(self, actor_eid, actor_comps, gauge, flow, context):
        flow.active_actor_id = actor_eid

        # ターゲットの最終決定
        target_id, target_part = self._resolve_target(actor_eid, actor_comps, gauge)
        
        # 攻撃アクションを選んだのにターゲットが見つからない場合（全滅やロスト）
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
        
        # 攻撃の場合はここで事前計算を行う
        if gauge.selected_action == ActionType.ATTACK:
            event.calculation_result = CombatService.calculate_combat_result(
                self.world, actor_eid, target_id, target_part, gauge.selected_part
            )

        self.world.add_component(event_eid, event)
        flow.processing_event_id = event_eid
        
        # フェーズ移行
        if gauge.selected_action == ActionType.ATTACK:
            flow.current_phase = BattlePhase.TARGET_INDICATION
            flow.phase_timer = BattleTiming.TARGET_INDICATION
        else:
            flow.current_phase = BattlePhase.EXECUTING
        
        # 待機列から削除
        if context.waiting_queue and context.waiting_queue[0] == actor_eid:
            context.waiting_queue.pop(0)

    def _handle_target_loss(self, actor_eid, actor_comps, gauge, flow, context):
        """ターゲットが見つからなかった場合の中断処理"""
        actor_name = actor_comps['medal'].nickname
        
        # LogServiceを利用
        context.battle_log.append(LogService.get_target_lost(actor_name))
        
        flow.current_phase = BattlePhase.LOG_WAIT
        
        reset_gauge_to_cooldown(gauge)
        
        if context.waiting_queue and context.waiting_queue[0] == actor_eid:
            context.waiting_queue.pop(0)

    def _resolve_target(self, actor_eid, actor_comps, gauge):
        """アクションタイプと武器特性に応じてターゲットを決定する"""
        if gauge.selected_action != ActionType.ATTACK or not gauge.selected_part:
            return None, None

        part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
        if not part_id:
            return None, None
            
        part_comps = self.world.try_get_entity(part_id)
        if not part_comps:
            return None, None

        attack_comp = part_comps.get('attack')
        if not attack_comp:
            return None, None

        if attack_comp.trait in TraitType.MELEE_TRAITS:
            return self._resolve_melee_target(actor_comps)
        else:
            return self._resolve_shooting_target(gauge)

    def _resolve_melee_target(self, actor_comps):
        target_id = get_closest_target_by_gauge(self.world, actor_comps['team'].team_type)
        target_part = self._select_random_alive_part(target_id)
        return target_id, target_part

    def _resolve_shooting_target(self, gauge):
        if not gauge.selected_part:
            return None, None
            
        target_data = gauge.part_targets.get(gauge.selected_part)
        if target_data:
            tid, tpart = target_data
            if is_target_valid(self.world, tid, tpart):
                return tid, tpart
        return None, None

    def _select_random_alive_part(self, target_id):
        t_comps = self.world.try_get_entity(target_id)
        if not t_comps:
            return None
            
        alive_parts = []
        for pt, pid in t_comps['partlist'].parts.items():
            p_comps = self.world.try_get_entity(pid)
            if p_comps and p_comps['health'].hp > 0:
                alive_parts.append(pt)
                
        return random.choice(alive_parts) if alive_parts else None