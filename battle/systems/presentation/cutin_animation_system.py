"""カットイン演出管理システム"""

from core.ecs import System
from battle.constants import BattlePhase, BattleTiming
from battle.service.flow_service import transition_to_phase, get_battle_state

class CutinAnimationSystem(System):
    """
    CUTINフェーズの時間管理を行い、
    演出が終了したらEXECUTINGフェーズへ遷移させる。
    """
    def update(self, dt: float):
        _, flow = get_battle_state(self.world)
        if not flow or flow.current_phase != BattlePhase.CUTIN:
            return

        flow.phase_timer -= dt
        max_time = BattleTiming.CUTIN_ANIMATION
        elapsed = max(0.0, max_time - flow.phase_timer)
        flow.cutin_progress = min(1.0, elapsed / max_time)
        
        if flow.phase_timer <= 0:
            transition_to_phase(flow, BattlePhase.EXECUTING)
            flow.cutin_progress = 1.0