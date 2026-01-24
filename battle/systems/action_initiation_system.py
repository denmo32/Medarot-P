"""行動開始起案システム"""

from core.ecs import System
from components.action_event import ActionEventComponent
from battle.constants import GaugeStatus, ActionType, BattlePhase, PartType, BattleTiming
from battle.service.combat_service import CombatService

class ActionInitiationSystem(System):
    """
    1. 行動開始の起案システム
    チャージ完了したエンティティに対し、ターゲットを確定し、
    **CombatServiceを使用して事前に戦闘計算を行って** ActionEventを生成する。
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
        
        # 攻撃の場合はCombatServiceで事前計算を行う
        if gauge.selected_action == ActionType.ATTACK:
            self._process_combat_calculation(actor_eid, target_id, target_part, gauge.selected_part, event)

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

    def _process_combat_calculation(self, attacker_id, target_id, target_desired_part, attacker_part_type, event):
        """Worldからデータを収集し、CombatServiceに計算を依頼する"""
        
        # 1. コンポーネント取得
        attacker_comps = self.world.try_get_entity(attacker_id)
        target_comps = self.world.try_get_entity(target_id)
        
        if not attacker_comps or not target_comps:
            event.calculation_result = None
            return

        # 2. 攻撃側データの収集
        atk_part_id = attacker_comps['partlist'].parts.get(attacker_part_type)
        atk_part_comps = self.world.try_get_entity(atk_part_id)
        if not atk_part_comps or 'attack' not in atk_part_comps:
            event.calculation_result = None
            return
            
        attack_comp = atk_part_comps['attack']
        atk_medal = attacker_comps.get('medal')
        atk_part = atk_part_comps.get('part')
        
        attacker_data = {
            'medal_attr': atk_medal.attribute if atk_medal else "undefined",
            'part_attr': atk_part.attribute if atk_part else "undefined",
            'attack_val': attack_comp.attack,
            'success_val': attack_comp.success,
            'trait': attack_comp.trait
        }

        # 3. 防御側データの収集
        tgt_medal = target_comps.get('medal')
        mobility, defense = self._get_target_legs_stats(target_comps)
        
        target_data = {
            'medal_attr': tgt_medal.attribute if tgt_medal else "undefined",
            'mobility': mobility,
            'defense': defense,
            'desired_part': target_desired_part
        }
        
        # 4. 生存パーツマップの作成 {part_type: hp}
        target_alive_parts = {}
        for pt, pid in target_comps['partlist'].parts.items():
            p_comps = self.world.try_get_entity(pid)
            if p_comps and p_comps['health'].hp > 0:
                target_alive_parts[pt] = p_comps['health'].hp

        # 5. Service呼び出し
        event.calculation_result = CombatService.calculate_combat_result(
            attacker_data, 
            target_data, 
            target_alive_parts
        )

    def _get_target_legs_stats(self, target_comps):
        """ターゲットの脚部性能（機動・防御）を取得"""
        legs_id = target_comps['partlist'].parts.get(PartType.LEGS)
        legs_comps = self.world.try_get_entity(legs_id) if legs_id is not None else None
        
        if legs_comps:
            mob_comp = legs_comps.get('mobility')
            if mob_comp:
                return mob_comp.mobility, mob_comp.defense
        return 0, 0

    def _handle_target_loss(self, actor_eid, actor_comps, gauge, flow, context):
        """ターゲットが見つからなかった場合の中断処理"""
        actor_name = actor_comps['medal'].nickname
        context.battle_log.append(f"{actor_name}はターゲットロストした！")
        
        # 本来はGaugeSystemの責務だが、フロー制御をここに記述してしまっている（後のリファクタリング対象）
        from battle.utils import reset_gauge_to_cooldown
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

        from battle.constants import TraitType
        if attack_comp.trait in TraitType.MELEE_TRAITS:
            return self._resolve_melee_target(actor_comps)
        else:
            return self._resolve_shooting_target(gauge)

    def _resolve_melee_target(self, actor_comps):
        from battle.utils import get_closest_target_by_gauge
        target_id = get_closest_target_by_gauge(self.world, actor_comps['team'].team_type)
        target_part = self._select_random_alive_part(target_id)
        return target_id, target_part

    def _resolve_shooting_target(self, gauge):
        from battle.utils import is_target_valid
        if not gauge.selected_part:
            return None, None
            
        target_data = gauge.part_targets.get(gauge.selected_part)
        if target_data:
            tid, tpart = target_data
            if is_target_valid(self.world, tid, tpart):
                return tid, tpart
        return None, None

    def _select_random_alive_part(self, target_id):
        import random
        t_comps = self.world.try_get_entity(target_id)
        if not t_comps:
            return None
            
        alive_parts = []
        for pt, pid in t_comps['partlist'].parts.items():
            p_comps = self.world.try_get_entity(pid)
            if p_comps and p_comps['health'].hp > 0:
                alive_parts.append(pt)
                
        return random.choice(alive_parts) if alive_parts else None