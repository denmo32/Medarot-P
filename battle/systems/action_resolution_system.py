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
            
            if not part_id or part_id not in self.world.entities:
                context.battle_log.append(f"{attacker_name}の攻撃！ しかしパーツが破損している！")
                flow.current_phase = BattlePhase.LOG_WAIT
                self._reset_gauge(attacker_comps)
                return

            attack_comp = self.world.entities[part_id].get('attack')
            if not attack_comp:
                context.battle_log.append(f"{attacker_name}の攻撃失敗！")
                flow.current_phase = BattlePhase.LOG_WAIT
                self._reset_gauge(attacker_comps)
                return

            target_id = event.current_target_id
            
            if target_id and target_id in self.world.entities:
                context.battle_log.append(f"{attacker_name}の攻撃！ {attack_comp.trait}！")
                
                # 命中・防御・クリティカル判定
                hit_result = self._process_attack_logic(target_id, attack_comp)
                is_hit, is_defense, is_critical, damage, target_part, stop_duration = hit_result
                
                if not is_hit:
                    context.pending_logs.append("攻撃を回避！")
                else:
                    if is_critical:
                        context.pending_logs.append("クリティカルヒット！")
                    elif is_defense:
                        context.pending_logs.append("攻撃を防御！")
                    else:
                        context.pending_logs.append("ノーマルヒット！")
                    
                    # ダメージイベント発行
                    self.world.add_component(target_id, DamageEventComponent(
                        attacker_id, event.part_type, damage, target_part, is_critical, stop_duration
                    ))

                flow.current_phase = BattlePhase.LOG_WAIT
            else:
                context.battle_log.append(f"{attacker_name}の攻撃！ しかし対象がいない！")
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

    def _process_attack_logic(self, target_id, attack_comp):
        """
        命中判定、防御判定、クリティカル判定、ダメージ計算、状態異常計算を行う
        return: (is_hit, is_defense, is_critical, damage, target_part, stop_duration)
        """
        target_comps = self.world.entities[target_id]
        
        # 1. パラメータ取得
        success = attack_comp.success
        
        legs_id = target_comps['partlist'].parts.get(PartType.LEGS)
        mobility = 0
        defense = 0
        
        if legs_id and legs_id in self.world.entities:
            mob_comp = self.world.entities[legs_id].get('mobility')
            if mob_comp:
                mobility = mob_comp.mobility
                defense = mob_comp.defense

        # 2. 確率計算 (命中率 & 防御突破率)
        hit_prob = calculate_hit_probability(success, mobility)
        break_prob = calculate_break_probability(success, defense)

        # 3. 乱数生成
        rnd_hit = random.random()
        rnd_break = random.random()

        # 4. 余剰計算
        margin_hit = hit_prob - rnd_hit
        margin_break = break_prob - rnd_break

        is_hit = False
        is_defense = False
        is_critical = False

        # 5. 判定ロジック
        if margin_hit < 0:
            # 回避成功 (Miss)
            return False, False, False, 0, None, 0.0
        
        is_hit = True

        if margin_break < 0:
            # 防御発生 (Guard) - 突破失敗
            is_defense = True
            # 防御された場合はクリティカルなし
        else:
            # 防御突破 (Clean Hit)
            # クリティカル判定: 両方の余剰の合計が一定値を超えた場合
            # (例: 閾値0.5)
            if (margin_hit + margin_break) > 0.5:
                is_critical = True

        # 6. ターゲット部位決定
        alive_parts = [p for p, pid in target_comps['partlist'].parts.items() 
                       if self.world.entities[pid]['health'].hp > 0]
        target_part = random.choice(alive_parts) if alive_parts else PartType.HEAD

        # 7. ダメージ計算
        damage = calculate_damage(attack_comp.attack, success, mobility, defense, is_critical)

        # 8. 状態異常：サンダーによる「停止」
        stop_duration = 0.0
        if attack_comp.trait == TraitType.THUNDER:
            # 停止時間 = (攻撃成功度 - 相手機動) * 係数（最低でもわずかに停止する）
            stop_duration = max(0.5, (success - mobility) * 0.5)

        return True, is_defense, is_critical, damage, target_part, stop_duration