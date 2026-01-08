"""行動実行パイプラインシステム群"""

import random
from core.ecs import System
from components.battle_flow import BattleFlowComponent
from components.action_event import ActionEventComponent
from components.battle import DamageEventComponent
from battle.utils import calculate_current_x

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
        if flow.current_phase != BattleFlowComponent.PHASE_IDLE:
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
        if gauge.status == gauge.CHARGING and gauge.progress >= 100.0:
            self._initiate_action(actor_eid, actor_comps, gauge, flow, context)

    def _initiate_action(self, actor_eid, actor_comps, gauge, flow, context):
        # ターゲット確定
        target_id = None
        
        if gauge.selected_action == "attack" and gauge.selected_part:
            part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
            if part_id and part_id in self.world.entities:
                attack_comp = self.world.entities[part_id].get('attack')
                target_id = self._determine_target(actor_eid, actor_comps, gauge, attack_comp)
        
        # ActionEventエンティティ生成
        event_eid = self.world.create_entity()
        self.world.add_component(event_eid, ActionEventComponent(
            attacker_id=actor_eid,
            action_type=gauge.selected_action,
            part_type=gauge.selected_part,
            target_id=target_id
        ))
        
        # フェーズ移行
        flow.current_phase = BattleFlowComponent.PHASE_EXECUTING
        flow.processing_event_id = event_eid
        
        # 待機列から削除
        if context.waiting_queue and context.waiting_queue[0] == actor_eid:
            context.waiting_queue.pop(0)

    def _determine_target(self, eid, comps, gauge, attack_comp):
        target_id = None
        if attack_comp and attack_comp.trait in ["ソード", "ハンマー"]:
            # 直前ターゲット：現在のアイコン座標が最も中央に近い敵を狙う
            target_id = self._get_closest_target(eid, comps['team'].team_type)
        else:
            # 事前ターゲット
            if gauge.selected_part:
                target_id = gauge.part_targets.get(gauge.selected_part)
        
        # 救済措置（対象が既に倒れている、または見つからない場合）
        if not target_id or target_id not in self.world.entities or self.world.entities[target_id]['defeated'].is_defeated:
            target_id = self._get_fallback_target(comps['team'].team_type)
        return target_id

    def _get_closest_target(self, eid, my_team):
        target_team = "enemy" if my_team == "player" else "player"
        best_target = None
        extreme_x = float('inf') if my_team == "player" else float('-inf')
        
        for teid, tcomps in self.world.get_entities_with_components('team', 'defeated', 'position', 'gauge'):
            if tcomps['team'].team_type == target_team and not tcomps['defeated'].is_defeated:
                cur_x = calculate_current_x(
                    tcomps['position'].x, 
                    tcomps['gauge'].status, 
                    tcomps['gauge'].progress, 
                    tcomps['team'].team_type
                )
                if my_team == "player":
                    if cur_x < extreme_x:
                        extreme_x = cur_x
                        best_target = teid
                else:
                    if cur_x > extreme_x:
                        extreme_x = cur_x
                        best_target = teid
        return best_target

    def _get_fallback_target(self, my_team):
        target_team = "enemy" if my_team == "player" else "player"
        alive = [teid for teid, tcomps in self.world.get_entities_with_components('team', 'defeated') 
                 if tcomps['team'].team_type == target_team and not tcomps['defeated'].is_defeated]
        return random.choice(alive) if alive else None


class ActionResolutionSystem(System):
    """
    2. 行動解決システム
    ActionEventが存在する場合、その内容を実行（ダメージ計算など）し、イベントを終了させる。
    """
    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        if flow.current_phase != BattleFlowComponent.PHASE_EXECUTING:
            return
        
        event_eid = flow.processing_event_id
        if not event_eid or event_eid not in self.world.entities:
            # 何らかの理由でイベントがない場合はIDLEに戻す
            flow.current_phase = BattleFlowComponent.PHASE_IDLE
            flow.processing_event_id = None
            return

        event = self.world.entities[event_eid]['actionevent']
        
        # ここで実行処理（解決）
        self._resolve_action(event, context, flow)
        
        # イベントエンティティの破棄とIDクリア
        self.world.delete_entity(event_eid)
        flow.processing_event_id = None

    def _resolve_action(self, event, context, flow):
        attacker_id = event.attacker_id
        attacker_comps = self.world.entities.get(attacker_id)
        
        # 攻撃者が既に存在しない（倒された等）場合のガード
        if not attacker_comps: 
            return

        attacker_name = attacker_comps['medal'].nickname
        
        if event.action_type == "attack":
            part_id = attacker_comps['partlist'].parts.get(event.part_type)
            
            # パーツIDが無効な場合のガード
            if not part_id or part_id not in self.world.entities:
                context.battle_log.append(f"{attacker_name}の攻撃！ しかしパーツが破損している！")
                flow.current_phase = BattleFlowComponent.PHASE_LOG_WAIT
                self._reset_gauge(attacker_comps)
                return

            attack_comp = self.world.entities[part_id].get('attack')
            # 攻撃コンポーネントがない場合のガード
            if not attack_comp:
                context.battle_log.append(f"{attacker_name}の攻撃失敗！")
                flow.current_phase = BattleFlowComponent.PHASE_LOG_WAIT
                self._reset_gauge(attacker_comps)
                return

            target_id = event.current_target_id
            
            if target_id and target_id in self.world.entities:
                # ログ
                context.battle_log.append(f"{attacker_name}の攻撃！ {attack_comp.trait}！")
                
                # 命中・ダメージ計算
                hit_result = self._calculate_hit_and_damage(target_id, attack_comp)
                is_hit, is_defense, damage, target_part = hit_result
                
                if not is_hit:
                    context.pending_logs.append("攻撃を回避された！")
                else:
                    if is_defense:
                        context.pending_logs.append("防御判定に成功！(ダメージ軽減未実装)")
                    
                    # ダメージイベント発行
                    self.world.add_component(target_id, DamageEventComponent(attacker_id, event.part_type, damage, target_part))

                flow.current_phase = BattleFlowComponent.PHASE_LOG_WAIT
            else:
                context.battle_log.append(f"{attacker_name}の攻撃！ しかし対象がいない！")
                flow.current_phase = BattleFlowComponent.PHASE_LOG_WAIT

        elif event.action_type == "skip":
            context.battle_log.append(f"{attacker_name}は行動をスキップ！")
            flow.current_phase = BattleFlowComponent.PHASE_LOG_WAIT
        
        else:
            # 未知のアクションタイプの場合
            flow.current_phase = BattleFlowComponent.PHASE_IDLE

        # 実行完了後のゲージリセット
        self._reset_gauge(attacker_comps)

    def _reset_gauge(self, attacker_comps):
        gauge = attacker_comps['gauge']
        gauge.status = gauge.COOLDOWN
        gauge.progress = 0.0
        gauge.selected_action = None
        gauge.selected_part = None

    def _calculate_hit_and_damage(self, target_id, attack_comp):
        """
        命中判定、防御判定、ダメージ計算を行い結果を返す
        return: (is_hit, is_defense, damage, target_part)
        """
        target_comps = self.world.entities[target_id]
        
        # 1. パラメータ取得
        success = attack_comp.success # 成功度
        
        # 回避度（脚部）
        legs_id = target_comps['partlist'].parts.get('legs')
        mobility = 0
        if legs_id and legs_id in self.world.entities:
            mob_comp = self.world.entities[legs_id].get('mobility')
            if mob_comp:
                mobility = mob_comp.mobility

        # 防御度（威力平均）
        total_attack = 0
        count = 0
        for p_key in ['head', 'right_arm', 'left_arm']:
            pid = target_comps['partlist'].parts.get(p_key)
            if pid and pid in self.world.entities:
                # 破壊されていても計算に含める
                ac = self.world.entities[pid].get('attack')
                if ac:
                    total_attack += ac.attack
                    count += 1
        defense = total_attack / count if count > 0 else 0

        # 2. 回避判定
        # 命中率 = 成功度 / (成功度 + 回避度 * 係数)
        mobility_weight = 0.25
        hit_prob = success / (success + (mobility * mobility_weight)) if (success + (mobility * mobility_weight)) > 0 else 1.0
        is_hit = random.random() < hit_prob

        if not is_hit:
            return False, False, 0, None

        # 3. 防御判定
        # 防御成功率 = 防御度 / (成功度 + 防御度)
        defend_prob = defense / (success + defense) if (success + defense) > 0 else 0.0
        is_defense = random.random() < defend_prob
        
        # 4. ターゲット部位決定（既存ロジック）
        alive_parts = [p for p, pid in target_comps['partlist'].parts.items() 
                       if self.world.entities[pid]['health'].hp > 0]
        target_part = random.choice(alive_parts) if alive_parts else "head"

        # 5. ダメージ計算
        # ダメージ = 基本威力 + max(0, 成功度 - 回避度/2 - 防御度/2)
        bonus = max(0, success - (mobility / 2) - (defense / 2))
        damage = int(attack_comp.attack + bonus)

        return True, is_defense, damage, target_part