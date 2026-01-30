"""ターゲット演出のフロー制御システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.flow import FlowMechanics, transition_to_phase

class TargetIndicatorSystem(BattleSystemBase):
    def update(self, dt: float):
        context, flow = self.battle_state
        if not context or flow.current_phase != BattlePhase.TARGET_INDICATION:
            return

        flow.phase_timer -= dt
        
        if flow.phase_timer <= 0:
            # 次の遷移情報をMechanicsから取得
            transition = FlowMechanics.resolve_indicator_transition(self.world, flow.processing_event_id)
            
            # Side Effects
            if transition.logs:
                context.battle_log.extend(transition.logs)
                
            transition_to_phase(flow, transition.next_phase, transition.timer)