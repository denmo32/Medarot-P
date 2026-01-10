"""行動解決システム"""

import random
from core.ecs import System
from components.battle_flow import BattleFlowComponent
from components.battle import DamageEventComponent
from battle.constants import ActionType, GaugeStatus, BattlePhase, PartType, TraitType
from battle.calculator import calculate_hit_probability, calculate_break_probability, calculate_damage

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
            flow.current_phase = BattlePhase.IDLE
            flow.processing_event_id = None
            return

        event = self.world.entities[event_eid]['actionevent']
        
        self._resolve_action(event, context, flow)
        
        self.world.delete_entity(event_eid)
        flow.processing_event_id = None

    def _resolve_action(self, event, context, flow):
        attacker_id = event.attacker_id
        attacker_comps = self.world.entities.get(attacker_id)
        
        if not attacker_comps: 
            return

        attacker_name = attacker_comps['medal'].nickname
        
        if event.action_type == ActionType.ATTACK:
            part_id = attacker_comps['partlist'].parts.get(event.part_type)
            
            # 実行直前のパーツ破壊チェック（念のため）
            if not part_id or self.world.entities[part_id]['health'].hp <= 0:
                context.battle_log.append(f"{attacker_name}の攻撃！ しかしパーツが破損している！")
                flow.current_phase = BattlePhase.LOG_WAIT
                self._reset_gauge(attacker_comps)
                return

            attack_comp = self.world.entities[part_id].get('attack')
            target_id = event.current_target_id
            
            # ターゲットの存在チェック（念のため）
            if target_id and target_id in self.world.entities and not self.world.entities[target_id]['defeated'].is_defeated:
                context.battle_log.append(f"{attacker_name}の攻撃！ {attack_comp.trait}！")
                
                # 命中・防御・クリティカル判定
                hit_result = self._process_attack_logic(target_id, attack_comp, event.desired_target_part)
                is_hit, is_defense, is_critical, damage, target_part, stop_duration = hit_result
                
                if not is_hit:
                    context.pending_logs.append("攻撃を回避！")
                else:
                    if is_critical:
                        context.pending_logs.append("クリティカルヒット！")
                    elif is_defense:
                        context.pending_logs.append("攻撃を防御！")
                    else:
                        context.pending_logs.append("防御突破！クリーンヒット！")
                    
                    # ダメージイベント発行
                    self.world.add_component(target_id, DamageEventComponent(
                        attacker_id, event.part_type, damage, target_part, is_critical, stop_duration
                    ))

                flow.current_phase = BattlePhase.LOG_WAIT
            else:
                context.battle_log.append(f"{attacker_name}はターゲットロストした！")
                flow.current_phase = BattlePhase.LOG_WAIT

        elif event.action_type == ActionType.SKIP:
            context.battle_log.append(f"{attacker_name}は行動をスキップ！")
            flow.current_phase = BattlePhase.LOG_WAIT
        
        else:
            flow.current_phase = BattlePhase.IDLE

        self._reset_gauge(attacker_comps)

    def _reset_gauge(self, attacker_comps):
        gauge = attacker_comps['gauge']
        gauge.status = GaugeStatus.COOLDOWN
        gauge.progress = 0.0
        gauge.selected_action = None
        gauge.selected_part = None

    def _process_attack_logic(self, target_id, attack_comp, desired_part):
        """命中・ダメージ計算"""
        target_comps = self.world.entities[target_id]
        
        # パラメータ取得
        success = attack_comp.success
        legs_id = target_comps['partlist'].parts.get(PartType.LEGS)
        mobility, defense = 0, 0
        if legs_id and legs_id in self.world.entities:
            mob_comp = self.world.entities[legs_id].get('mobility')
            if mob_comp:
                mobility, defense = mob_comp.mobility, mob_comp.defense

        # 判定
        hit_prob = calculate_hit_probability(success, mobility)
        break_prob = calculate_break_probability(success, defense)
        rnd_hit, rnd_break = random.random(), random.random()
        margin_hit, margin_break = hit_prob - rnd_hit, break_prob - rnd_break

        if margin_hit < 0:
            return False, False, False, 0, None, 0.0
        
        is_hit = True
        is_defense = (margin_break < 0)
        is_critical = (not is_defense and (margin_hit + margin_break) > 0.5)

        # 生存パーツ情報の収集
        alive_keys = [p_type for p_type, p_id in target_comps['partlist'].parts.items() 
                      if self.world.entities[p_id]['health'].hp > 0]
        
        target_part = PartType.HEAD
        if is_defense:
            # 防御成功時: 頭部以外でHP最大のパーツを選択
            non_head_parts = [p for p in alive_keys if p != PartType.HEAD]
            if non_head_parts:
                non_head_parts.sort(key=lambda p: self.world.entities[target_comps['partlist'].parts[p]]['health'].hp, reverse=True)
                target_part = non_head_parts[0]
        else:
            # 防御失敗時: 狙った部位が生存していればそれ。なければ生存パーツからランダム。
            if desired_part and desired_part in alive_keys:
                target_part = desired_part
            elif alive_keys:
                target_part = random.choice(alive_keys)

        damage = calculate_damage(attack_comp.attack, success, mobility, defense, is_critical, is_defense)

        stop_duration = 0.0
        if attack_comp.trait == TraitType.THUNDER:
            stop_duration = max(0.5, (success - mobility) * 0.5)

        return True, is_defense, is_critical, damage, target_part, stop_duration