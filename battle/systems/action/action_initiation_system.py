"""行動開始起案システム"""

from battle.systems.battle_system_base import BattleSystemBase
from components.action_event_component import ActionEventComponent
from battle.mechanics.flow import PhaseTransition
from domain.constants import GaugeStatus, ActionType
from battle.constants import BattlePhase, BattleTiming
from battle.mechanics.combat import CombatMechanics
from battle.mechanics.action import ActionMechanics
from battle.mechanics.action_behavior import ActionBehaviorRegistry
from battle.mechanics.log import LogBuilder

class ActionInitiationSystem(BattleSystemBase):
    """
    充填が完了したエンティティに対し、ActionEventを生成してバトルフローを開始する。
    """
    def update(self, dt: float):
        if not self.context or self.flow.current_phase != BattlePhase.IDLE or not self.context.waiting_queue:
            return

        actor_eid = self.context.waiting_queue[0]
        actor_comps = self.get_comps(actor_eid, 'gauge', 'team', 'partlist', 'medal')
        if not actor_comps:
            self.manage_queue(actor_eid, False)
            return

        gauge = actor_comps['gauge']
        # 充填完了チェック
        if gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0:
            self._initiate_action(actor_eid, actor_comps, gauge)

    def _initiate_action(self, actor_eid, actor_comps, gauge):
        """行動開始の具体処理"""
        # 行動種別に応じた振る舞いを取得
        behavior = ActionBehaviorRegistry.get(gauge.selected_action)
        
        # 1. ターゲット解決
        target_id, target_part = behavior.initiate(self.world, actor_eid, actor_comps, gauge)
        
        # ターゲットロスト時の中断処理
        if not target_id:
            msg = LogBuilder.get_target_lost(actor_comps['medal'].nickname)
            reset = ActionMechanics.get_cooldown_reset_data(gauge.progress)
            
            self.apply_gauge_reset(actor_eid, reset)
            self.manage_queue(actor_eid, False)
            self.apply_phase_transition(PhaseTransition(next_phase=BattlePhase.LOG_WAIT, logs=[msg]))
            return

        # 2. ActionEventの生成
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
            event.calculation_result = CombatMechanics.calculate_combat_result(
                self.world, actor_eid, target_id, target_part, gauge.selected_part
            )

        self.world.add_component(event_eid, event)
        
        # 3. フェーズ遷移（Behaviorに依存）
        next_p = behavior.get_initial_phase()
        timer = BattleTiming.TARGET_INDICATION if next_p == BattlePhase.TARGET_INDICATION else 0.0
        
        self.apply_phase_transition(PhaseTransition(
            next_phase=next_p,
            timer=timer,
            actor_id=actor_eid,
            event_id=event_eid
        ))
        
        self.manage_queue(actor_eid, False)