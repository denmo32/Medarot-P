"""行動解決システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.flow import transition_to_phase
from battle.mechanics.action_behavior import ActionBehaviorRegistry
from components.battle_component import DamageEventComponent

class ActionResolutionSystem(BattleSystemBase):
    """
    演出が終了した段階で呼ばれ、ActionEvent 結果を世界に反映する。
    """
    def update(self, dt: float):
        if not self.flow or self.flow.current_phase != BattlePhase.EXECUTING:
            return
        
        event_eid = self.flow.processing_event_id
        event_comps = self.get_comps(event_eid, 'actionevent') if event_eid is not None else None
        
        if not event_comps:
            transition_to_phase(self.flow, BattlePhase.IDLE)
            return

        # 行動の解決（Mechanicsへの委譲）
        event = event_comps['actionevent']
        attacker_comps = self.get_comps(event.attacker_id, 'medal', 'partlist', 'gauge')
        
        if attacker_comps:
            behavior = ActionBehaviorRegistry.get(event.action_type)
            
            # 1. 結果オブジェクトの取得（純粋な判断）
            result = behavior.resolve(self.world, event, self.context)
            
            # 2. 世界への適用（副作用の集中実行）
            if result.logs:
                self.context.battle_log.extend(result.logs)
                
            if result.damage_result:
                dr = result.damage_result
                # ダメージ指示書からECSコンポーネントを生成して付与
                damage_comp = DamageEventComponent(
                    attacker_id=dr.attacker_id,
                    attacker_part=dr.attacker_part,
                    damage=dr.damage,
                    target_part=dr.target_part,
                    is_critical=dr.is_critical,
                    added_effects=dr.added_effects
                )
                self.world.add_component(event.current_target_id, damage_comp)

            if result.gauge_reset:
                gr = result.gauge_reset
                gauge = attacker_comps['gauge']
                gauge.status = gr.status
                gauge.progress = gr.progress
                if gr.clear_selection:
                    gauge.selected_action = None
                    gauge.selected_part = None
                    gauge.part_targets = {}
            
            if result.should_remove_from_queue:
                if event.attacker_id in self.context.waiting_queue:
                    self.context.waiting_queue.remove(event.attacker_id)

            # 3. フェーズ遷移
            transition_to_phase(self.flow, result.next_phase, result.phase_timer)
        
        # 解決後、特定の待機フェーズ以外ならクリーンアップ
        if self.flow.current_phase not in [BattlePhase.CUTIN_RESULT, BattlePhase.LOG_WAIT]:
            self._cleanup_event(event_eid)

    def _cleanup_event(self, event_eid):
        self.world.delete_entity(event_eid)
        self.flow.processing_event_id = None