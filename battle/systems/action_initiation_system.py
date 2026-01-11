"""行動開始起案システム"""

import random
from core.ecs import System
from components.action_event import ActionEventComponent
from battle.utils import get_closest_target_by_gauge, reset_gauge_to_cooldown
from battle.constants import GaugeStatus, ActionType, BattlePhase, TraitType

class ActionInitiationSystem(System):
    """
    1. 行動開始の起案システム
    チャージ完了したエンティティがあれば、ActionEventを生成してフェーズをEXECUTINGに移行する。
    """
    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        if flow.current_phase != BattlePhase.IDLE:
            return
        
        if not context.waiting_queue:
            return

        actor_eid = context.waiting_queue[0]
        if actor_eid not in self.world.entities:
            context.waiting_queue.pop(0)
            return

        actor_comps = self.world.entities[actor_eid]
        gauge = actor_comps['gauge']
        
        # チャージ完了（100%）しているか確認
        if gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0:
            self._initiate_action(actor_eid, actor_comps, gauge, flow, context)

    def _initiate_action(self, actor_eid, actor_comps, gauge, flow, context):
        flow.active_actor_id = actor_eid

        # ターゲット確定
        target_id, target_part = self._resolve_target(actor_eid, actor_comps, gauge)
        
        # 攻撃アクションでターゲット不在の場合は中断
        if gauge.selected_action == ActionType.ATTACK and not target_id:
            actor_name = actor_comps['medal'].nickname
            context.battle_log.append(f"{actor_name}はターゲットロストした！")
            flow.current_phase = BattlePhase.LOG_WAIT
            
            # クールダウンへ移行（実行ラインからの帰還）
            reset_gauge_to_cooldown(gauge)
            if context.waiting_queue and context.waiting_queue[0] == actor_eid:
                context.waiting_queue.pop(0)
            return

        # ActionEventエンティティ生成
        event_eid = self.world.create_entity()
        self.world.add_component(event_eid, ActionEventComponent(
            attacker_id=actor_eid,
            action_type=gauge.selected_action,
            part_type=gauge.selected_part,
            target_id=target_id,
            target_part=target_part
        ))
        
        # フェーズ移行
        flow.current_phase = BattlePhase.EXECUTING
        flow.processing_event_id = event_eid
        
        # 待機列から削除
        if context.waiting_queue and context.waiting_queue[0] == actor_eid:
            context.waiting_queue.pop(0)

    def _resolve_target(self, actor_eid, actor_comps, gauge):
        """アクションタイプに応じてターゲットを決定する"""
        target_id = None
        target_part = None
        
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
            if part_id and part_id in self.world.entities:
                attack_comp = self.world.entities[part_id].get('attack')
                target_id, target_part = self._determine_target(actor_eid, actor_comps, gauge, attack_comp)
        
        return target_id, target_part

    def _determine_target(self, eid, comps, gauge, attack_comp):
        target_id = None
        target_part = None

        # 近接攻撃特性の判定（一番近い敵を狙う）
        if attack_comp and attack_comp.trait in [TraitType.SWORD, TraitType.HAMMER, TraitType.THUNDER]:
            target_id = get_closest_target_by_gauge(self.world, comps['team'].team_type)
            if target_id:
                target_part = self._select_random_alive_part(target_id)
        else:
            # 事前ターゲット（射撃系）
            if gauge.selected_part:
                target_data = gauge.part_targets.get(gauge.selected_part)
                if target_data:
                    tid, tpart = target_data
                    if self._is_target_valid(tid, tpart):
                        target_id, target_part = tid, tpart
        
        return target_id, target_part

    def _is_target_valid(self, target_id, target_part):
        if not target_id or target_id not in self.world.entities:
            return False
        t_comps = self.world.entities[target_id]
        if t_comps['defeated'].is_defeated:
            return False
        p_id = t_comps['partlist'].parts.get(target_part)
        if not p_id or self.world.entities[p_id]['health'].hp <= 0:
            return False
        return True

    def _select_random_alive_part(self, target_id):
        if target_id not in self.world.entities:
            return None
        t_comps = self.world.entities[target_id]
        alive_parts = [pt for pt, pid in t_comps['partlist'].parts.items() 
                       if self.world.entities[pid]['health'].hp > 0]
        return random.choice(alive_parts) if alive_parts else None