"""ターゲット演出のフロー制御システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.flow import FlowMechanics

class TargetIndicatorSystem(BattleSystemBase):
    """ターゲット指示演出の進行管理"""

    def update(self, dt: float):
        context = self.state.context
        flow = self.state.flow
        
        if not context or flow.current_phase != BattlePhase.TARGET_INDICATION:
            return

        flow.phase_timer -= dt

        if flow.phase_timer <= 0:
            # 次の遷移情報を Mechanics から取得
            transition = FlowMechanics.resolve_indicator_transition(self.state, flow.processing_event_id)
            # 副作用を適用
            self.state.apply_phase_transition(transition)
