"""行動開始起案システム"""

import random
from core.ecs import System
from components.action_event import ActionEventComponent
from battle.utils import get_closest_target_by_gauge, reset_gauge_to_cooldown, is_target_valid
from battle.constants import GaugeStatus, ActionType, BattlePhase, TraitType, PartType
from battle.calculator import (
    calculate_hit_probability, 
    calculate_break_probability, 
    check_is_hit,
    check_attack_outcome,
    calculate_damage
)

class ActionInitiationSystem(System):
    """
    1. 行動開始の起案システム
    チャージ完了したエンティティに対し、ターゲットを確定し、
    **事前に戦闘計算を行って** ActionEventを生成する。
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
            self._pre_calculate_combat(actor_eid, target_id, target_part, gauge.selected_part, event)

        self.world.add_component(event_eid, event)
        flow.processing_event_id = event_eid
        
        # フェーズ移行
        if gauge.selected_action == ActionType.ATTACK:
            flow.current_phase = BattlePhase.TARGET_INDICATION
            flow.phase_timer = 0.8 # 演出時間(秒)
        else:
            flow.current_phase = BattlePhase.EXECUTING
        
        # 待機列から削除
        if context.waiting_queue and context.waiting_queue[0] == actor_eid:
            context.waiting_queue.pop(0)

    def _pre_calculate_combat(self, attacker_id, target_id, target_desired_part, attacker_part_type, event):
        """戦闘結果を事前に計算し、イベントコンポーネントに保存する"""
        attacker_comps = self.world.try_get_entity(attacker_id)
        target_comps = self.world.try_get_entity(target_id)
        
        if not attacker_comps or not target_comps:
            event.calculation_result = None
            return

        # 攻撃パーツ情報の取得
        atk_part_id = attacker_comps['partlist'].parts.get(attacker_part_type)
        atk_part_comps = self.world.try_get_entity(atk_part_id)
        if not atk_part_comps or 'attack' not in atk_part_comps:
            event.calculation_result = None
            return
            
        attack_comp = atk_part_comps['attack']

        # A. ステータス取得
        success = attack_comp.success
        mobility, defense = self._get_target_legs_stats(target_comps)

        # B. 確率計算
        hit_prob = calculate_hit_probability(success, mobility)
        break_prob = calculate_break_probability(success, defense)
        
        # C. 命中判定
        is_hit = check_is_hit(hit_prob)
        
        if not is_hit:
            # 回避された場合
            event.calculation_result = {
                'is_hit': False,
                'is_critical': False,
                'is_defense': False,
                'damage': 0,
                'hit_part': None,
                'stop_duration': 0.0
            }
            return

        # D. 判定詳細（クリティカル・防御）
        is_critical, is_defense = check_attack_outcome(hit_prob, break_prob)

        # E. 命中部位の決定（防御発生時は「かばう」挙動）
        hit_part = self._determine_hit_part(target_comps, target_desired_part, is_defense)
        
        # F. ダメージ計算
        damage = calculate_damage(attack_comp.attack, success, mobility, defense, is_critical, is_defense)
        
        # G. 追加効果
        stop_duration = self._calculate_stop_effect(attack_comp, success, mobility)

        # 結果の保存
        event.calculation_result = {
            'is_hit': True,
            'is_critical': is_critical,
            'is_defense': is_defense,
            'damage': damage,
            'hit_part': hit_part,
            'stop_duration': stop_duration
        }

    def _get_target_legs_stats(self, target_comps):
        """ターゲットの脚部性能（機動・防御）を取得"""
        legs_id = target_comps['partlist'].parts.get(PartType.LEGS)
        legs_comps = self.world.try_get_entity(legs_id) if legs_id is not None else None
        
        if legs_comps:
            mob_comp = legs_comps.get('mobility')
            if mob_comp:
                return mob_comp.mobility, mob_comp.defense
        return 0, 0

    def _determine_hit_part(self, target_comps, desired_part, is_defense):
        """実際に命中する部位を決定する"""
        # 生存パーツのリストとマップ
        alive_parts_map = {}
        for pt, pid in target_comps['partlist'].parts.items():
             p_comps = self.world.try_get_entity(pid)
             if p_comps and p_comps['health'].hp > 0:
                 alive_parts_map[pt] = pid
                 
        alive_keys = list(alive_parts_map.keys())

        if is_defense:
            # 防御成功時は「頭部以外」かつ「HP最大」のパーツがかばう
            non_head = [p for p in alive_keys if p != PartType.HEAD]
            if non_head:
                non_head.sort(
                    key=lambda p: self.world.entities[alive_parts_map[p]]['health'].hp, 
                    reverse=True
                )
                return non_head[0]
            return PartType.HEAD
        
        else:
            # 防御失敗時は狙った部位へ
            if desired_part and desired_part in alive_keys:
                return desired_part
            elif alive_keys:
                return random.choice(alive_keys)
        
        return PartType.HEAD

    def _calculate_stop_effect(self, attack_comp, success, mobility):
        """サンダー攻撃などの停止時間を計算"""
        if attack_comp.trait == TraitType.THUNDER:
            return max(0.5, (success - mobility) * 0.05)
        return 0.0

    def _handle_target_loss(self, actor_eid, actor_comps, gauge, flow, context):
        """ターゲットが見つからなかった場合の中断処理"""
        actor_name = actor_comps['medal'].nickname
        context.battle_log.append(f"{actor_name}はターゲットロストした！")
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