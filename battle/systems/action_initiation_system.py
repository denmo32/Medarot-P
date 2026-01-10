"""行動開始起案システム"""

import random
from core.ecs import System
from components.battle_flow import BattleFlowComponent
from components.action_event import ActionEventComponent
from battle.utils import get_closest_target_by_gauge
from battle.constants import GaugeStatus, ActionType, PartType, TeamType, BattlePhase, TraitType

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

        # IDLE状態以外では新たな行動を開始しない
        if flow.current_phase != BattlePhase.IDLE:
            return
        
        if not context.waiting_queue:
            return

        # 待機列先頭のエンティティをチェック
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
        # アクティブな行動者を設定
        flow.active_actor_id = actor_eid

        # ターゲット確定
        target_id = None
        target_part = None
        
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
            if part_id and part_id in self.world.entities:
                attack_comp = self.world.entities[part_id].get('attack')
                target_id, target_part = self._determine_target(actor_eid, actor_comps, gauge, attack_comp)
        
        # ターゲットが取得できなかった場合はターゲットロストとして中断
        if gauge.selected_action == ActionType.ATTACK and not target_id:
            actor_name = actor_comps['medal'].nickname
            context.battle_log.append(f"{actor_name}はターゲットロストした！")
            flow.current_phase = BattlePhase.LOG_WAIT
            self._reset_to_cooldown(gauge, context, actor_eid)
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

    def _determine_target(self, eid, comps, gauge, attack_comp):
        target_id = None
        target_part = None

        # 近接攻撃特性の判定
        if attack_comp and attack_comp.trait in [TraitType.SWORD, TraitType.HAMMER, TraitType.THUNDER]:
            target_id = get_closest_target_by_gauge(self.world, comps['team'].team_type)
            if target_id:
                target_part = self._select_random_alive_part(target_id)
        else:
            # 事前ターゲット
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

    def _reset_to_cooldown(self, gauge, context, eid):
        """
        アクションを中断してその地点からクールダウンへ移行。
        実行ライン(100%)での中断なので、progressを0(実行ライン地点)にする。
        """
        gauge.status = GaugeStatus.COOLDOWN
        gauge.progress = 0.0
        gauge.selected_action = None
        gauge.selected_part = None
        if context.waiting_queue and context.waiting_queue[0] == eid:
            context.waiting_queue.pop(0)