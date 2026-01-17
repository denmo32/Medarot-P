"""行動解決システム"""

import random
from core.ecs import System
from components.battle import DamageEventComponent
from battle.constants import ActionType, BattlePhase, PartType, TraitType
from battle.calculator import (
    calculate_hit_probability, 
    calculate_break_probability, 
    check_is_hit,
    check_attack_outcome,
    calculate_damage
)
from battle.utils import reset_gauge_to_cooldown

class ActionResolutionSystem(System):
    """
    2. 行動解決システム
    ActionEventを実行し、命中判定・ダメージ計算を行い、DamageEventを発行する。
    """
    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        if flow.current_phase != BattlePhase.EXECUTING:
            return
        
        event_eid = flow.processing_event_id
        event_comps = self.world.try_get_entity(event_eid) if event_eid is not None else None
        
        if not event_comps or 'actionevent' not in event_comps:
            flow.current_phase = BattlePhase.IDLE
            flow.processing_event_id = None
            return

        event = event_comps['actionevent']
        
        # アクションの実行
        self._resolve_action(event, context, flow)
        
        # CUTIN_RESULTへ移行する場合はイベントをまだ削除しない（RenderSystemで情報を使うため）
        # SKIP等でLOG_WAITに行く場合は削除する
        if flow.current_phase != BattlePhase.CUTIN_RESULT:
            self.world.delete_entity(event_eid)
            flow.processing_event_id = None
        
        # イベントエンティティの削除を InputSystem._handle_cutin_result に委譲する形になる。

    def _resolve_action(self, event, context, flow):
        attacker_id = event.attacker_id
        attacker_comps = self.world.try_get_entity(attacker_id)
        
        if not attacker_comps: return

        if event.action_type == ActionType.ATTACK:
            self._handle_attack_action(event, attacker_comps, context)
            # 攻撃の場合はカットイン結果表示へ
            flow.current_phase = BattlePhase.CUTIN_RESULT
        elif event.action_type == ActionType.SKIP:
            context.battle_log.append(f"{attacker_comps['medal'].nickname}は行動をスキップ！")
            flow.current_phase = BattlePhase.LOG_WAIT

        # どのアクションであれ、終了後はクールダウンへ
        if 'gauge' in attacker_comps:
            reset_gauge_to_cooldown(attacker_comps['gauge'])

    def _handle_attack_action(self, event, attacker_comps, context):
        attacker_name = attacker_comps['medal'].nickname
        part_id = attacker_comps['partlist'].parts.get(event.part_type)
        
        # 1. 自身の攻撃パーツ生存チェック
        part_comps = self.world.try_get_entity(part_id) if part_id is not None else None
        if not part_comps or part_comps['health'].hp <= 0:
            context.battle_log.append(f"{attacker_name}の攻撃！ しかしパーツが破損している！")
            return

        attack_comp = part_comps.get('attack')
        target_id = event.current_target_id
        target_comps = self.world.try_get_entity(target_id) if target_id is not None else None
        
        # 2. ターゲット存在チェック
        if not target_comps or target_comps['defeated'].is_defeated:
            context.battle_log.append(f"{attacker_name}はターゲットロストした！")
            return
        
        # 3. 計算実行
        self._execute_combat_calculations(event.attacker_id, target_id, target_comps, event, attack_comp, context)

    def _execute_combat_calculations(self, attacker_id, target_id, target_comps, event, attack_comp, context):
        """戦闘計算のメインロジック"""
        
        # A. ステータス取得
        success = attack_comp.success
        mobility, defense = self._get_target_legs_stats(target_comps)

        # B. 確率計算
        hit_prob = calculate_hit_probability(success, mobility)
        break_prob = calculate_break_probability(success, defense)
        
        # C. 命中判定
        if not check_is_hit(hit_prob):
            context.pending_logs.append("攻撃を回避！")
            return

        # D. 判定詳細（クリティカル・防御）
        is_critical, is_defense = check_attack_outcome(hit_prob, break_prob)

        # E. 命中部位の決定（防御発生時は「かばう」挙動）
        hit_part = self._determine_hit_part(target_comps, event.desired_target_part, is_defense)
        
        # F. ダメージ計算
        damage = calculate_damage(attack_comp.attack, success, mobility, defense, is_critical, is_defense)
        
        # G. ログと追加効果
        self._queue_combat_logs(context, is_critical, is_defense)
        stop_duration = self._calculate_stop_effect(attack_comp, success, mobility)

        # H. ダメージイベント発行
        self.world.add_component(target_id, DamageEventComponent(
            attacker_id, event.part_type, damage, hit_part, is_critical, stop_duration
        ))

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
        """
        実際に命中する部位を決定する。
        防御成功時: 「かばう」が発動し、頭部以外の最もHPが高いパーツに当たる。
        防御失敗時: 狙った部位に当たる（部位破壊済みの場合はランダム）。
        """
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
                # HP降順でソート (ECSアクセスしてHP比較)
                non_head.sort(
                    key=lambda p: self.world.entities[alive_parts_map[p]]['health'].hp, 
                    reverse=True
                )
                return non_head[0]
            # 頭しか残ってなければ頭に当たる
            return PartType.HEAD
        
        else:
            # 防御失敗時は狙った部位へ
            if desired_part and desired_part in alive_keys:
                return desired_part
            elif alive_keys:
                return random.choice(alive_keys)
        
        return PartType.HEAD # フォールバック

    def _queue_combat_logs(self, context, is_critical, is_defense):
        if is_critical:
            context.pending_logs.append("クリティカルヒット！")
        elif is_defense:
            context.pending_logs.append("攻撃を防御！")
        else:
            context.pending_logs.append("防御突破！クリーンヒット！")

    def _calculate_stop_effect(self, attack_comp, success, mobility):
        """サンダー攻撃などの停止時間を計算"""
        if attack_comp.trait == TraitType.THUNDER:
            # 成功度が相手の機動を上回るほど長く止める
            return max(0.5, (success - mobility) * 0.05)
        return 0.0