"""行動開始起案システム"""

from typing import Optional
from battle.systems.battle_system_base import BattleSystemBase
from components.action_event_component import ActionEventComponent
from domain.flow import PhaseTransition, FlowMechanics
from domain.constants import GaugeStatus, ActionType, PartType
from battle.constants import BattlePhase, BattleTiming
from domain.combat_stats import CombatStats, MedalParams, AttackParams, LegsStats
from domain.damage import CombatResult, calculate_damage_result
from domain.action import ActionMechanics, GaugeResetData, ActionInterruptionResult
from domain.skill import SkillRegistry
from domain.trait import TraitRegistry
from domain.log import LogBuilder
from systems.utils.targeting_utils import TargetingUtils


class ActionInitiationSystem(BattleSystemBase):
    """
    充填が完了したエンティティに対し、ActionEvent を生成してバトルフローを開始する。
    """
    def update(self, dt: float):
        context = self.context
        flow = self.flow

        if not context or flow.current_phase != BattlePhase.IDLE or not context.waiting_queue:
            return

        actor_eid = context.waiting_queue[0]
        actor_comps = self.world.try_get_entity(actor_eid)

        # エンティティが存在しない、または機能停止している場合はキューから削除
        defeated = actor_comps.get('defeated') if actor_comps else None
        if not actor_comps or (defeated and defeated.is_defeated):
            FlowMechanics.manage_queue(context, actor_eid, False)
            return

        required = ['gauge', 'team', 'partlist', 'medal']
        if not all(k in actor_comps for k in required):
            FlowMechanics.manage_queue(context, actor_eid, False)
            return

        gauge = actor_comps['gauge']
        # 充填完了チェック
        if gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0:
            self._initiate_action(actor_eid, actor_comps, gauge)

    def _initiate_action(self, actor_eid: int, actor_comps: dict, gauge):
        """行動開始の具体処理"""
        from domain.personality import PersonalityRegistry
        
        # 行動種別に応じた振る舞いを取得
        # TODO: ActionBehaviorRegistry は domain/action_behavior.py へ移動予定
        
        # System 側で必要なデータを抽出して純粋関数に渡す
        # 1. 実行パーツの生存チェック
        is_actor_part_alive = True
        attack_trait = ""
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            is_actor_part_alive = TargetingUtils.is_part_alive(self.world, actor_eid, gauge.selected_part)
            # 攻撃パーツの特性情報を取得
            actor_comps = self.world.try_get_entity(actor_eid)
            if actor_comps and 'partlist' in actor_comps:
                part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
                if part_id:
                    p_comps = self.world.try_get_entity(part_id)
                    if p_comps and 'attack' in p_comps:
                        attack_trait = p_comps['attack'].trait

        # 2. TargetResolver によるターゲット解決
        #    System は「どの Resolver を使うか」だけを知り、「どう解決するか」は知らない
        # TODO: TargetResolverFactory も整理が必要
        from battle.mechanics.targeting_resolvers import TargetResolverFactory
        resolver = TargetResolverFactory.get(attack_trait)
        resolved_target_id, resolved_target_part = resolver.resolve(
            actor_eid=actor_eid,
            selected_part=gauge.selected_part,
            world=self.world
        )

        # 3. パラメータ構築（InitiateParams はシンプルに）
        # TODO: InitiateParams もデータクラスとして定義し直す
        from dataclasses import dataclass
        from typing import Optional
        
        @dataclass
        class InitiateParams:
            selected_action: str
            selected_part: Optional[str]
            is_actor_part_alive: bool
            attack_trait: str
            resolved_target_id: Optional[int]
            resolved_target_part: Optional[str]
        
        params = InitiateParams(
            selected_action=gauge.selected_action,
            selected_part=gauge.selected_part,
            is_actor_part_alive=is_actor_part_alive,
            attack_trait=attack_trait,
            resolved_target_id=resolved_target_id,
            resolved_target_part=resolved_target_part
        )

        # TODO: behavior.initiate() の呼び出しも整理
        from battle.mechanics.action_behavior import ActionBehaviorRegistry
        behavior = ActionBehaviorRegistry.get(gauge.selected_action)
        target_id, target_part = behavior.initiate(params)

        # ターゲットロスト時の中断処理
        if not target_id:
            msg = LogBuilder.get_target_lost(actor_comps['medal'].nickname)
            reset = ActionMechanics.get_cooldown_reset_data(gauge.progress, use_penalty=True)

            comps = self.world.try_get_entity(actor_eid)
            if comps and 'gauge' in comps:
                ActionMechanics.apply_gauge_reset(comps['gauge'], reset)
            FlowMechanics.manage_queue(self.context, actor_eid, False)
            FlowMechanics.apply_transition(self.world, PhaseTransition(next_phase=BattlePhase.LOG_WAIT, logs=[msg]))
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

        FlowMechanics.apply_transition(self.world, PhaseTransition(
            next_phase=next_p,
            timer=timer,
            actor_id=actor_eid,
            event_id=event_eid
        ))

        FlowMechanics.manage_queue(self.context, actor_eid, False)

    def _calculate_combat(
        self,
        actor_eid: int,
        attacker_part_type: str,
        target_id: int,
        target_desired_part: Optional[str]
    ):
        """戦闘計算を実行する"""
        # 1. パラメータ収集（System で直接抽出）
        attacker_comps = self.world.try_get_entity(actor_eid)
        if not attacker_comps or 'medal' not in attacker_comps:
            return None
            
        attacker_medal = MedalParams(attribute=attacker_comps['medal'].attribute)
        
        # 攻撃パーツのパラメータ
        if 'partlist' not in attacker_comps:
            return None
        part_id = attacker_comps['partlist'].parts.get(attacker_part_type)
        if not part_id:
            return None
        p_comps = self.world.try_get_entity(part_id)
        if not p_comps or 'attack' not in p_comps or 'part' not in p_comps:
            return None
        
        attack_comp = p_comps['attack']
        part_comp = p_comps['part']
        attacker_part = AttackParams(
            success=attack_comp.success,
            attack=attack_comp.attack,
            part_attribute=part_comp.attribute,
            skill_type=attack_comp.skill_type,
            trait=attack_comp.trait
        )
        
        # 脚部ステータス
        legs_id = attacker_comps['partlist'].parts.get(PartType.LEGS)
        if legs_id:
            legs_comps = self.world.try_get_entity(legs_id)
            if legs_comps and 'mobility' in legs_comps:
                attacker_legs = LegsStats(
                    mobility=legs_comps['mobility'].mobility,
                    defense=legs_comps['mobility'].defense
                )
            else:
                attacker_legs = LegsStats(mobility=0, defense=0)
        else:
            attacker_legs = LegsStats(mobility=0, defense=0)

        # ターゲットのパラメータ
        target_comps = self.world.try_get_entity(target_id)
        if not target_comps or 'medal' not in target_comps:
            return None
        target_medal = MedalParams(attribute=target_comps['medal'].attribute)
        
        # ターゲット脚部
        target_legs_id = target_comps.get('partlist', {}).parts.get(PartType.LEGS) if 'partlist' in target_comps else None
        if target_legs_id:
            target_legs_comps = self.world.try_get_entity(target_legs_id)
            if target_legs_comps and 'mobility' in target_legs_comps:
                target_legs = LegsStats(
                    mobility=target_legs_comps['mobility'].mobility,
                    defense=target_legs_comps['mobility'].defense
                )
            else:
                target_legs = LegsStats(mobility=0, defense=0)
        else:
            target_legs = LegsStats(mobility=0, defense=0)
        
        # ターゲットゲージデータ
        target_gauge = target_comps.get('gauge')
        target_gauge_status = target_gauge.status if target_gauge else ""
        target_selected_part = target_gauge.selected_part if target_gauge else None
        
        target_part_skill_type = None
        if target_selected_part and 'partlist' in target_comps:
            t_part_id = target_comps['partlist'].parts.get(target_selected_part)
            if t_part_id:
                t_p_comps = self.world.try_get_entity(t_part_id)
                if t_p_comps and 'attack' in t_p_comps:
                    target_part_skill_type = t_p_comps['attack'].skill_type

        if not all([attacker_medal, attacker_part, target_medal]):
            return None

        # 対象の生存パーツ HP
        target_part_hps = TargetingUtils.get_alive_parts_hp(self.world, target_id)

        # 2. ステータス補正計算
        from domain.combat_stats import calculate_adjusted_stats, get_defensive_penalty, calculate_hit_probability_with_penalty
        
        stats = calculate_adjusted_stats(
            attacker_medal=attacker_medal,
            attacker_part=attacker_part,
            attacker_legs=attacker_legs,
            target_medal=target_medal,
            target_legs=target_legs
        )

        penalty = get_defensive_penalty(
            target_gauge_status=target_gauge_status,
            target_selected_part=target_selected_part,
            target_part_skill_type=target_part_skill_type
        )

        # 3. 命中判定
        hit_prob, is_hit = calculate_hit_probability_with_penalty(stats, penalty)
        if not is_hit:
            return CombatResult.miss()

        # 4. ダメージ計算
        return calculate_damage_result(
            attack_trait=attacker_part.trait,
            stats=stats,
            hit_prob=hit_prob,
            target_part_hps=target_part_hps,
            target_desired_part=target_desired_part,
            prevent_defense=penalty.prevent_defense
        )
