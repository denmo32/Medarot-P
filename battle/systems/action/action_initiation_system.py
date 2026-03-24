"""行動開始起案システム"""

from typing import Optional
from battle.systems.battle_system_base import BattleSystemBase
from components.action_event_component import ActionEventComponent
from battle.mechanics.flow import PhaseTransition, FlowMechanics
from domain.constants import GaugeStatus, ActionType, PartType
from battle.constants import BattlePhase, BattleTiming
from battle.mechanics.combat import CombatMechanics
from battle.mechanics.action import ActionMechanics
from battle.mechanics.action_behavior import ActionBehaviorRegistry, InitiateParams
from battle.mechanics.log import LogBuilder
from battle.mechanics.hit_calculator import AttackParams, MedalParams, LegsStats
from battle.mechanics.targeting_resolvers import TargetResolverFactory
from battle.mechanics.targeting import TargetingMechanics


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
        # 行動種別に応じた振る舞いを取得
        behavior = ActionBehaviorRegistry.get(gauge.selected_action)

        # System 側で必要なデータを抽出して純粋関数に渡す
        # 1. 実行パーツの生存チェック
        is_actor_part_alive = True
        attack_trait = ""
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            is_actor_part_alive = TargetingMechanics.is_part_alive(self.world, actor_eid, gauge.selected_part)
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
        resolver = TargetResolverFactory.get(attack_trait)
        resolved_target_id, resolved_target_part = resolver.resolve(
            actor_eid=actor_eid,
            selected_part=gauge.selected_part,
            world=self.world
        )

        # 3. パラメータ構築（InitiateParams はシンプルに）
        params = InitiateParams(
            selected_action=gauge.selected_action,
            selected_part=gauge.selected_part,
            is_actor_part_alive=is_actor_part_alive,
            attack_trait=attack_trait,
            resolved_target_id=resolved_target_id,
            resolved_target_part=resolved_target_part
        )

        target_id, target_part = behavior.initiate(params)

        # ターゲットロスト時の中断処理
        if not target_id:
            msg = LogBuilder.get_target_lost(actor_comps['medal'].nickname)
            reset = ActionMechanics.get_cooldown_reset_data(gauge.progress)

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
        # 攻撃者情報の取得
        attacker_comps = self.world.try_get_entity(actor_eid)
        if not attacker_comps:
            return None

        # メダル情報
        medal_attr = attacker_comps['medal'].attribute
        attacker_medal = MedalParams(attribute=medal_attr)

        # 攻撃パーツ情報
        attack_comp = None
        part_comp = None
        if 'partlist' in attacker_comps:
            part_id = attacker_comps['partlist'].parts.get(attacker_part_type)
            if part_id:
                p_comps = self.world.try_get_entity(part_id)
                if p_comps and 'attack' in p_comps and 'part' in p_comps:
                    attack_comp = p_comps['attack']
                    part_comp = p_comps['part']
        
        if not attack_comp or not part_comp:
            return None

        attacker_part = AttackParams(
            success=attack_comp.success,
            attack=attack_comp.attack,
            part_attribute=part_comp.attribute,
            skill_type=attack_comp.skill_type,
            trait=attack_comp.trait
        )

        # 脚部情報
        attacker_legs = LegsStats(mobility=0, defense=0)
        if 'partlist' in attacker_comps:
            legs_id = attacker_comps['partlist'].parts.get(PartType.LEGS)
            if legs_id:
                legs_comps = self.world.try_get_entity(legs_id)
                if legs_comps and 'mobility' in legs_comps:
                    attacker_legs = LegsStats(
                        mobility=legs_comps['mobility'].mobility,
                        defense=legs_comps['mobility'].defense
                    )

        # ターゲット情報
        target_comps = self.world.try_get_entity(target_id)
        if not target_comps:
            return None

        target_medal = MedalParams(attribute=target_comps['medal'].attribute)

        # ターゲットの脚部情報
        target_legs = LegsStats(mobility=0, defense=0)
        if 'partlist' in target_comps:
            target_legs_id = target_comps['partlist'].parts.get(PartType.LEGS)
            if target_legs_id:
                target_legs_comps = self.world.try_get_entity(target_legs_id)
                if target_legs_comps and 'mobility' in target_legs_comps:
                    target_legs = LegsStats(
                        mobility=target_legs_comps['mobility'].mobility,
                        defense=target_legs_comps['mobility'].defense
                    )

        # ターゲットのゲージ情報
        target_gauge = target_comps.get('gauge')
        target_gauge_status = target_gauge.status if target_gauge else ""
        target_selected_part = target_gauge.selected_part if target_gauge else None

        # ターゲットの選択中パーツのスキル情報
        target_part_skill_type = None
        if target_selected_part and 'partlist' in target_comps:
            target_part_id = target_comps['partlist'].parts.get(target_selected_part)
            if target_part_id:
                tgt_p_comps = self.world.try_get_entity(target_part_id)
                if tgt_p_comps and 'attack' in tgt_p_comps:
                    target_part_skill_type = tgt_p_comps['attack'].skill_type

        # 対象の生存パーツ HP
        target_part_hps = TargetingMechanics.get_alive_parts_hp(self.world, target_id)

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
