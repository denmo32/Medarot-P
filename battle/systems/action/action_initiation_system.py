"""行動開始起案システム"""

from typing import Optional, Dict, Any
from battle.systems.base.battle_system_base import BattleSystemBase
from components.action_event_component import ActionEventComponent
from domain.constants import GaugeStatus, ActionType, PartType
from battle.constants import BattlePhase, BattleTiming
from domain.action_logic import get_action_behavior, get_cooldown_reset_data, InitiateParams
from domain.log_logic import get_target_lost
from domain.flow_logic import PhaseTransition
from battle.systems.decision.target_resolver import TargetResolverFactory


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
            self.remove_from_queue(actor_eid)
            return

        required = ['gauge', 'team', 'partlist', 'medal']
        if not all(k in actor_comps for k in required):
            self.remove_from_queue(actor_eid)
            return

        gauge = actor_comps['gauge']
        # 充填完了チェック
        if gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0:
            self._initiate_action(actor_eid, actor_comps, gauge)

    def _initiate_action(self, actor_eid: int, actor_comps: dict, gauge):
        """行動開始の具体処理"""
        # 行動種別に応じた振る舞いを取得
        behavior = get_action_behavior(gauge.selected_action)

        # 1. 実行パーツの生存チェック
        is_actor_part_alive = True
        attack_trait = ""
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            is_actor_part_alive = self.is_part_alive(actor_eid, gauge.selected_part)
            # 攻撃パーツの特性情報を取得
            if 'partlist' in actor_comps:
                part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
                if part_id:
                    p_comps = self.world.try_get_entity(part_id)
                    if p_comps and 'attack' in p_comps:
                        attack_trait = p_comps['attack'].trait

        # 2. TargetResolver によるターゲット解決
        resolver = TargetResolverFactory.get(attack_trait)
        resolved_target_id, resolved_target_part = resolver.resolve(
            actor_eid=actor_eid,
            selected_part=gauge.selected_part,
            world=self.world
        )

        # 3. パラメータ構築
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
            msg = get_target_lost(actor_comps['medal'].nickname)
            reset = get_cooldown_reset_data(gauge.progress, use_penalty=True)

            if 'gauge' in actor_comps:
                self.apply_gauge_reset(actor_comps['gauge'], reset)
            
            self.remove_from_queue(actor_eid)
            self.apply_transition(PhaseTransition(next_phase=BattlePhase.LOG_WAIT, logs=[msg]))
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
        self.world.add_component(event_eid, event)

        # 3. フェーズ遷移
        next_p = behavior.get_initial_phase()
        timer = BattleTiming.TARGET_INDICATION if next_p == BattlePhase.TARGET_INDICATION else 0.0

        self.apply_transition(PhaseTransition(
            next_phase=next_p,
            timer=timer,
            actor_id=actor_eid,
            event_id=event_eid
        ))

        self.remove_from_queue(actor_eid)

