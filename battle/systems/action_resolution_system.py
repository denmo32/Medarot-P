"""行動解決システム"""

import random
from core.ecs import System
from components.battle import DamageEventComponent
from battle.constants import ActionType, BattlePhase, PartType, TraitType
from battle.calculator import calculate_hit_probability, calculate_break_probability, calculate_damage
from battle.utils import reset_gauge_to_cooldown

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

        if event.action_type == ActionType.ATTACK:
            self._handle_attack_action(event, attacker_comps, context, flow)
        elif event.action_type == ActionType.SKIP:
            context.battle_log.append(f"{attacker_comps['medal'].nickname}は行動をスキップ！")
            flow.current_phase = BattlePhase.LOG_WAIT
        else:
            flow.current_phase = BattlePhase.IDLE

        # アクション終了後は常にクールダウンへ
        reset_gauge_to_cooldown(attacker_comps['gauge'])

    def _handle_attack_action(self, event, attacker_comps, context, flow):
        attacker_name = attacker_comps['medal'].nickname
        part_id = attacker_comps['partlist'].parts.get(event.part_type)
        
        # 実行直前のパーツ破壊チェック
        if not part_id or self.world.entities[part_id]['health'].hp <= 0:
            context.battle_log.append(f"{attacker_name}の攻撃！ しかしパーツが破損している！")
            flow.current_phase = BattlePhase.LOG_WAIT
            return

        attack_comp = self.world.entities[part_id].get('attack')
        target_id = event.current_target_id
        
        # ターゲット有効性チェック
        if target_id and target_id in self.world.entities and not self.world.entities[target_id]['defeated'].is_defeated:
            context.battle_log.append(f"{attacker_name}の攻撃！ {attack_comp.trait}！")
            self._execute_attack_calculations(event.attacker_id, target_id, event, attack_comp, context)
            flow.current_phase = BattlePhase.LOG_WAIT
        else:
            context.battle_log.append(f"{attacker_name}はターゲットロストした！")
            flow.current_phase = BattlePhase.LOG_WAIT

    def _execute_attack_calculations(self, attacker_id, target_id, event, attack_comp, context):
        """命中・ダメージ計算を実行し、結果をDamageEventとして発行"""
        target_comps = self.world.entities[target_id]
        
        # パラメータ取得
        success = attack_comp.success
        legs_id = target_comps['partlist'].parts.get(PartType.LEGS)
        mobility, defense = 0, 0
        if legs_id and legs_id in self.world.entities:
            mob_comp = self.world.entities[legs_id].get('mobility')
            if mob_comp:
                mobility, defense = mob_comp.mobility, mob_comp.defense

        # 命中・防御判定
        hit_prob = calculate_hit_probability(success, mobility)
        break_prob = calculate_break_probability(success, defense)
        
        is_hit = random.random() < hit_prob
        
        if not is_hit:
            context.pending_logs.append("攻撃を回避！")
            return

        is_defense = (random.random() > break_prob)
        is_critical = (not is_defense and (hit_prob + break_prob) > 1.5) # 簡易的なクリティカル判定式

        # 部位決定
        target_part = self._determine_hit_part(target_comps, event.desired_target_part, is_defense)
        
        # ダメージ計算
        damage = calculate_damage(attack_comp.attack, success, mobility, defense, is_critical, is_defense)
        
        # ログメッセージ準備
        if is_critical:
            context.pending_logs.append("クリティカルヒット！")
        elif is_defense:
            context.pending_logs.append("攻撃を防御！")
        else:
            context.pending_logs.append("防御突破！クリーンヒット！")
        
        stop_duration = 0.0
        if attack_comp.trait == TraitType.THUNDER:
            stop_duration = max(0.5, (success - mobility) * 0.5)

        # イベント発行
        self.world.add_component(target_id, DamageEventComponent(
            attacker_id, event.part_type, damage, target_part, is_critical, stop_duration
        ))

    def _determine_hit_part(self, target_comps, desired_part, is_defense):
        """防御状態などを考慮して、実際に命中する部位を決定する"""
        alive_keys = [p_type for p_type, p_id in target_comps['partlist'].parts.items() 
                      if self.world.entities[p_id]['health'].hp > 0]
        
        if is_defense:
            # 防御成功時: 頭部以外でHP最大のパーツが「かばう」
            non_head_parts = [p for p in alive_keys if p != PartType.HEAD]
            if non_head_parts:
                non_head_parts.sort(key=lambda p: self.world.entities[target_comps['partlist'].parts[p]]['health'].hp, reverse=True)
                return non_head_parts[0]
            # 頭部しか残っていない場合は頭部に当たる
            return PartType.HEAD
        else:
            # 防御失敗時: 狙った部位が生きていればそこ。なければランダム。
            if desired_part and desired_part in alive_keys:
                return desired_part
            elif alive_keys:
                return random.choice(alive_keys)
        
        return PartType.HEAD # フォールバック