"""行動解決システム"""

from battle.systems.battle_system_base import BattleSystemBase
from components.battle_component import DamageEventComponent
from battle.constants import ActionType, BattlePhase
from battle.mechanics.flow import transition_to_phase
from battle.mechanics.action import ActionMechanics
from battle.mechanics.action_behavior import ActionBehaviorRegistry

class ActionResolutionSystem(BattleSystemBase):
    """
    演出が終了した段階で呼ばれ、ActionEvent 結果を世界に反映する。
    具体的な反映ロジックは ActionBehavior に委譲する。
    """
    def update(self, dt: float):
        if not self.flow or self.flow.current_phase != BattlePhase.EXECUTING:
            return
        
        event_eid = self.flow.processing_event_id
        event_comps = self.get_comps(event_eid, 'actionevent') if event_eid is not None else None
        
        if not event_comps:
            transition_to_phase(self.flow, BattlePhase.IDLE)
            return

        # 行動の解決
        event = event_comps['actionevent']
        attacker_comps = self.get_comps(event.attacker_id, 'medal', 'partlist', 'gauge')
        
        if attacker_comps:
            behavior = ActionBehaviorRegistry.get(event.action_type)
            behavior.resolve(self.world, event, self.context, self.flow)
            
            # 実行後は常に放熱状態へリセット
            ActionMechanics.reset_to_cooldown(attacker_comps['gauge'])
        
        # 解決後、フェーズが CUTIN_RESULT 等に遷移していない場合はクリーンアップ
        if self.flow.current_phase not in [BattlePhase.CUTIN_RESULT, BattlePhase.LOG_WAIT]:
            self._cleanup_event(event_eid)

    def _cleanup_event(self, event_eid):
        self.world.delete_entity(event_eid)
        self.flow.processing_event_id = None