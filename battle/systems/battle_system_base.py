"""バトル系システムの基底クラス"""

from typing import Optional
from core.ecs import System
from battle.mechanics.flow import get_battle_state, PhaseTransition
from battle.mechanics.action import GaugeResetData
from battle.mechanics.action_behavior import ResolutionResult
from components.battle_component import DamageEventComponent

class BattleSystemBase(System):
    """BattleContextとBattleFlowへのアクセスと副作用適用を容易にする基底システム"""

    @property
    def battle_state(self):
        """(context, flow) のタプルを返す"""
        return get_battle_state(self.world)

    @property
    def context(self):
        """BattleContextComponent へのショートカットアクセス"""
        ctx, _ = get_battle_state(self.world)
        return ctx

    @property
    def flow(self):
        """BattleFlowComponent へのショートカットアクセス"""
        _, flow = get_battle_state(self.world)
        return flow

    # --- Side Effect Helpers (副作用の集中実行) ---

    def apply_phase_transition(self, transition: PhaseTransition):
        """フェーズ遷移指示をワールドに適用する"""
        flow = self.flow
        flow.current_phase = transition.next_phase
        flow.phase_timer = transition.timer
        
        if transition.actor_id is not None:
            flow.active_actor_id = transition.actor_id
        if transition.event_id is not None:
            flow.processing_event_id = transition.event_id
            
        if transition.logs:
            if transition.clear_logs:
                self.context.battle_log.clear()
            self.context.battle_log.extend(transition.logs)
            
        # IDLEへの遷移時はクリーンアップ
        from battle.constants import BattlePhase
        if transition.next_phase == BattlePhase.IDLE:
            flow.processing_event_id = None
            flow.active_actor_id = None
            flow.cutin_progress = 0.0

    def apply_gauge_reset(self, entity_id: int, reset_data: GaugeResetData):
        """ゲージリセット指示を適用する"""
        comps = self.world.try_get_entity(entity_id)
        if not comps or 'gauge' not in comps:
            return
            
        gauge = comps['gauge']
        gauge.status = reset_data.status
        gauge.progress = reset_data.progress
        
        if reset_data.clear_selection:
            gauge.selected_action = None
            gauge.selected_part = None
            gauge.part_targets = {}

    def manage_queue(self, entity_id: int, should_add: bool):
        """待機列への追加・削除を一括管理する"""
        queue = self.context.waiting_queue
        if should_add and entity_id not in queue:
            queue.append(entity_id)
        elif not should_add and entity_id in queue:
            queue.remove(entity_id)

    def apply_resolution_result(self, entity_id: int, result: ResolutionResult, event_id: Optional[int] = None):
        """アクション解決結果を適用する"""
        # ログの追加
        if result.logs:
            self.context.battle_log.extend(result.logs)
            
        # ダメージの発生
        if result.damage_result:
            dr = result.damage_result
            damage_comp = DamageEventComponent(
                attacker_id=dr.attacker_id,
                attacker_part=dr.attacker_part,
                damage=dr.damage,
                target_part=dr.target_part,
                is_critical=dr.is_critical,
                added_effects=dr.added_effects
            )
            # 現在のイベントターゲットを取得して付与
            if event_id is not None:
                event_comps = self.world.try_get_entity(event_id)
                if event_comps and 'actionevent' in event_comps:
                    target_id = event_comps['actionevent'].current_target_id
                    self.world.add_component(target_id, damage_comp)

        # ゲージのリセット
        if result.gauge_reset:
            self.apply_gauge_reset(entity_id, result.gauge_reset)
        
        # キューからの削除
        if result.should_remove_from_queue:
            self.manage_queue(entity_id, False)

        # フェーズ遷移
        self.apply_phase_transition(PhaseTransition(
            next_phase=result.next_phase,
            timer=result.phase_timer
        ))