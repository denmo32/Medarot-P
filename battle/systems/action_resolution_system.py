"""行動解決システム"""

import random
from core.ecs import System
from components.battle_flow import BattleFlowComponent
from components.battle import DamageEventComponent
from battle.constants import ActionType, GaugeStatus, BattlePhase, PartType
from battle.calculator import calculate_hit_probability, calculate_defense_probability, calculate_damage

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

        if flow.current_phase != BattlePhase.EXECUTING:
            return
        
        event_eid = flow.processing_event_id
        if not event_eid or event_eid not in self.world.entities:
            # 何らかの理由でイベントがない場合はIDLEに戻す
            flow.current_phase = BattlePhase.IDLE
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
        
        if event.action_type == ActionType.ATTACK:
            part_id = attacker_comps['partlist'].parts.get(event.part_type)
            
            # パーツIDが無効な場合のガード
            if not part_id or part_id not in self.world.entities:
                context.battle_log.append(f"{attacker_name}の攻撃！ しかしパーツが破損している！")
                flow.current_phase = BattlePhase.LOG_WAIT
                self._reset_gauge(attacker_comps)
                return

            attack_comp = self.world.entities[part_id].get('attack')
            # 攻撃コンポーネントがない場合のガード
            if not attack_comp:
                context.battle_log.append(f"{attacker_name}の攻撃失敗！")
                flow.current_phase = BattlePhase.LOG_WAIT
                self._reset_gauge(attacker_comps)
                return

            target_id = event.current_target_id
            
            if target_id and target_id in self.world.entities:
                # ログ
                context.battle_log.append(f"{attacker_name}の攻撃！ {attack_comp.trait}！")
                
                # 命中・ダメージ計算
                hit_result = self._process_attack_logic(target_id, attack_comp)
                is_hit, is_defense, damage, target_part = hit_result
                
                if not is_hit:
                    context.pending_logs.append("攻撃を回避された！")
                else:
                    if is_defense:
                        context.pending_logs.append("防御判定に成功！(ダメージ軽減未実装)")
                    
                    # ダメージイベント発行
                    self.world.add_component(target_id, DamageEventComponent(attacker_id, event.part_type, damage, target_part))

                flow.current_phase = BattlePhase.LOG_WAIT
            else:
                context.battle_log.append(f"{attacker_name}の攻撃！ しかし対象がいない！")
                flow.current_phase = BattlePhase.LOG_WAIT

        elif event.action_type == ActionType.SKIP:
            context.battle_log.append(f"{attacker_name}は行動をスキップ！")
            flow.current_phase = BattlePhase.LOG_WAIT
        
        else:
            # 未知のアクションタイプの場合
            flow.current_phase = BattlePhase.IDLE

        # 実行完了後のゲージリセット
        self._reset_gauge(attacker_comps)

    def _reset_gauge(self, attacker_comps):
        gauge = attacker_comps['gauge']
        gauge.status = GaugeStatus.COOLDOWN
        gauge.progress = 0.0
        gauge.selected_action = None
        gauge.selected_part = None

    def _process_attack_logic(self, target_id, attack_comp):
        """
        命中判定、防御判定、ダメージ計算を行い結果を返す
        return: (is_hit, is_defense, damage, target_part)
        """
        target_comps = self.world.entities[target_id]
        
        # 1. パラメータ取得
        success = attack_comp.success # 成功度
        
        # 回避度・防御度（脚部）
        legs_id = target_comps['partlist'].parts.get(PartType.LEGS)
        mobility = 0
        defense = 0
        
        if legs_id and legs_id in self.world.entities:
            mob_comp = self.world.entities[legs_id].get('mobility')
            if mob_comp:
                mobility = mob_comp.mobility
                defense = mob_comp.defense

        # 2. 回避判定
        hit_prob = calculate_hit_probability(success, mobility)
        is_hit = random.random() < hit_prob

        if not is_hit:
            return False, False, 0, None

        # 3. 防御判定
        defend_prob = calculate_defense_probability(success, defense)
        is_defense = random.random() < defend_prob
        
        # 4. ターゲット部位決定（既存ロジック）
        alive_parts = [p for p, pid in target_comps['partlist'].parts.items() 
                       if self.world.entities[pid]['health'].hp > 0]
        target_part = random.choice(alive_parts) if alive_parts else PartType.HEAD

        # 5. ダメージ計算
        damage = calculate_damage(attack_comp.attack, success, mobility, defense)

        return True, is_defense, damage, target_part