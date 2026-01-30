"""行動解決システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.flow import transition_to_phase
from battle.mechanics.action import ActionMechanics
from battle.mechanics.action_behavior import ActionBehaviorRegistry

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
            # 1. 結果オブジェクトの取得（判断）
            result = behavior.resolve(self.world, event, self.context)
            
            # 2. 世界への適用（副作用）
            if result.logs:
                self.context.battle_log.extend(result.logs)
                
            if result.damage_event:
                self.world.add_component(event.current_target_id, result.damage_event)

            if result.should_reset_gauge:
                ActionMechanics.reset_to_cooldown(attacker_comps['gauge'])
            
            # 3. フェーズ遷移
            transition_to_phase(self.flow, result.next_phase, result.phase_timer)
        
        # 解決後、特定の待機フェーズ以外ならクリーンアップ
        if self.flow.current_phase not in [BattlePhase.CUTIN_RESULT, BattlePhase.LOG_WAIT]:
            self._cleanup_event(event_eid)

    def _cleanup_event(self, event_eid):
        self.world.delete_entity(event_eid)
        self.flow.processing_event_id = None