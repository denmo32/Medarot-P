"""行動開始起案システム"""

from typing import Optional
from battle.systems.battle_system_base import BattleSystemBase
from components.action_event_component import ActionEventComponent
from battle.mechanics.flow import PhaseTransition
from domain.constants import GaugeStatus, ActionType, PartType
from battle.constants import BattlePhase, BattleTiming
from battle.mechanics.combat import CombatMechanics
from battle.mechanics.action import ActionMechanics
from battle.mechanics.action_behavior import ActionBehaviorRegistry, InitiateParams, ResolveContext
from battle.mechanics.log import LogBuilder
from battle.mechanics.hit_calculator import AttackParams, MedalParams, LegsStats

class ActionInitiationSystem(BattleSystemBase):
    """
    充填が完了したエンティティに対し、ActionEvent を生成してバトルフローを開始する。
    """
    def update(self, dt: float):
        context = self.query.context
        flow = self.query.flow

        if not context or flow.current_phase != BattlePhase.IDLE or not context.waiting_queue:
            return

        actor_eid = context.waiting_queue[0]
        actor_comps = self.world.try_get_entity(actor_eid)

        if not actor_comps:
            self.command.manage_queue(actor_eid, False)
            return

        required = ['gauge', 'team', 'partlist', 'medal']
        if not all(k in actor_comps for k in required):
            self.command.manage_queue(actor_eid, False)
            return

        gauge = actor_comps['gauge']
        # 充填完了チェック
        if gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0:
            self._initiate_action(actor_eid, actor_comps, gauge)

    def _initiate_action(self, actor_eid: int, actor_comps: dict, gauge):
        """行動開始の具体処理"""
        # 行動種別に応じた振る舞いを取得
        behavior = ActionBehaviorRegistry.get(gauge.selected_action)

        # System 側で必要なデータを抽出して純粋関数に渡す
        # 1. 実行パーツの生存チェック
        is_actor_part_alive = True
        attack_trait = ""
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            is_actor_part_alive = self.query.is_part_alive(actor_eid, gauge.selected_part)
            # 攻撃パーツの特性情報を取得
            p_comps = self.query.get_part_components(actor_eid, gauge.selected_part, 'attack')
            if p_comps:
                attack_trait = p_comps['attack'].trait

        # 2. ターゲットの生存チェック
        is_target_alive = True
        target_data = gauge.part_targets.get(gauge.selected_part)
        if target_data:
            target_id, target_part = target_data
            is_target_alive = self.query.is_part_alive(target_id, target_part)

        # 3. 格闘特性用の情報（closest enemy）
        closest_enemy_id = None
        personality_id = actor_comps['medal'].personality_id
        target_part_from_personality = None
        is_personality_target_alive = False
        
        if attack_trait in ["ソード", "サンダー", "ハンマー"]:  # 格闘特性
            from battle.mechanics.targeting import TargetingMechanics
            from domain.gauge_logic import calculate_gauge_ratio
            
            # 敵チームのゲージ情報を収集
            enemy_gauge_data = []
            target_team = "enemy" if actor_comps['team'].team_type == "player" else "player"
            
            for eid, ecomps in self.world.get_entities_with_components('team', 'defeated', 'gauge'):
                if ecomps['team'].team_type == target_team and not ecomps['defeated'].is_defeated:
                    ratio = calculate_gauge_ratio(ecomps['gauge'].status, ecomps['gauge'].progress)
                    enemy_gauge_data.append((eid, ecomps['gauge'].status, ecomps['gauge'].progress))
            
            closest_enemy_id = TargetingMechanics.get_closest_target_by_gauge(enemy_gauge_data)
            
            if closest_enemy_id:
                # 性格に基づいて部位を選択
                from battle.mechanics.personality import PersonalityRegistry
                personality = PersonalityRegistry.get(personality_id)
                alive_parts_hp = self.query.get_alive_parts_hp(closest_enemy_id)
                target_part_from_personality = personality.select_target_part(alive_parts_hp)
                is_personality_target_alive = True  # get_alive_parts_hp が返す時点で生存

        # 4. パーツターゲット情報
        part_targets = gauge.part_targets

        # ターゲット解決
        params = InitiateParams(
            selected_action=gauge.selected_action,
            selected_part=gauge.selected_part,
            is_actor_part_alive=is_actor_part_alive,
            attack_trait=attack_trait,
            part_targets=part_targets,
            is_target_alive=is_target_alive,
            closest_enemy_id=closest_enemy_id,
            personality_id=personality_id,
            target_part_from_personality=target_part_from_personality,
            is_personality_target_alive=is_personality_target_alive
        )
        
        target_id, target_part = behavior.initiate(params)

        # ターゲットロスト時の中断処理
        if not target_id:
            msg = LogBuilder.get_target_lost(actor_comps['medal'].nickname)
            reset = ActionMechanics.get_cooldown_reset_data(gauge.progress)

            self.command.apply_gauge_reset(actor_eid, reset)
            self.command.manage_queue(actor_eid, False)
            self.command.apply_phase_transition(PhaseTransition(next_phase=BattlePhase.LOG_WAIT, logs=[msg]))
            return

        # 2. ActionEvent の生成
        event_eid = self.world.create_entity()
        event = ActionEventComponent(
            attacker_id=actor_eid,
            action_type=gauge.selected_action,
            part_type=gauge.selected_part,
            target_id=target_id,
            target_part=target_part
        )

        # 攻撃の場合は事前に計算を実行
        if gauge.selected_action == ActionType.ATTACK:
            # 戦闘計算用のパラメータを収集
            combat_result = self._calculate_combat(actor_eid, gauge.selected_part, target_id, target_part)
            event.calculation_result = combat_result

        self.world.add_component(event_eid, event)

        # 3. フェーズ遷移（Behavior に依存）
        next_p = behavior.get_initial_phase()
        timer = BattleTiming.TARGET_INDICATION if next_p == BattlePhase.TARGET_INDICATION else 0.0

        self.command.apply_phase_transition(PhaseTransition(
            next_phase=next_p,
            timer=timer,
            actor_id=actor_eid,
            event_id=event_eid
        ))

        self.command.manage_queue(actor_eid, False)

    def _calculate_combat(
        self,
        actor_eid: int,
        attacker_part_type: str,
        target_id: int,
        target_desired_part: Optional[str]
    ):
        """戦闘計算を実行する"""
        # 攻撃者情報の取得
        attacker_comps = self.world.try_get_entity(actor_eid)
        if not attacker_comps:
            return None
        
        # メダル情報
        medal_attr = attacker_comps['medal'].attribute
        attacker_medal = MedalParams(attribute=medal_attr)
        
        # 攻撃パーツ情報
        atk_part_comps = self.query.get_part_components(actor_eid, attacker_part_type, 'attack', 'part')
        if not atk_part_comps:
            return None
        
        attack_comp = atk_part_comps['attack']
        part_comp = atk_part_comps['part']
        attacker_part = AttackParams(
            success=attack_comp.success,
            attack=attack_comp.attack,
            part_attribute=part_comp.attribute,
            skill_type=attack_comp.skill_type,
            trait=attack_comp.trait
        )
        
        # 脚部情報
        legs_comps = self.query.get_part_components(actor_eid, PartType.LEGS, 'mobility')
        attacker_legs = LegsStats(
            mobility=legs_comps['mobility'].mobility if legs_comps else 0,
            defense=legs_comps['mobility'].defense if legs_comps else 0
        )
        
        # ターゲット情報
        target_comps = self.world.try_get_entity(target_id)
        if not target_comps:
            return None
        
        target_medal = MedalParams(attribute=target_comps['medal'].attribute)
        
        target_legs_comps = self.query.get_part_components(target_id, PartType.LEGS, 'mobility')
        target_legs = LegsStats(
            mobility=target_legs_comps['mobility'].mobility if target_legs_comps else 0,
            defense=target_legs_comps['mobility'].defense if target_legs_comps else 0
        )
        
        # ターゲットのゲージ情報
        target_gauge = target_comps.get('gauge')
        target_gauge_status = target_gauge.status if target_gauge else ""
        target_selected_part = target_gauge.selected_part if target_gauge else None
        
        # ターゲットの選択中パーツのスキル情報
        target_part_skill_type = None
        if target_selected_part:
            tgt_p_comps = self.query.get_part_components(target_id, target_selected_part, 'attack')
            if tgt_p_comps:
                target_part_skill_type = tgt_p_comps['attack'].skill_type
        
        # 対象の生存パーツ HP
        target_part_hps = self.query.get_alive_parts_hp(target_id)
        
        # 戦闘計算実行
        return CombatMechanics.calculate_combat_result(
            attacker_medal=attacker_medal,
            attacker_part=attacker_part,
            attacker_legs=attacker_legs,
            target_medal=target_medal,
            target_legs=target_legs,
            target_gauge_status=target_gauge_status,
            target_selected_part=target_selected_part,
            target_part_skill_type=target_part_skill_type,
            target_part_hps=target_part_hps,
            target_desired_part=target_desired_part
        )
