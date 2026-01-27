"""カットイン演出管理システム"""

from core.ecs import System
from battle.constants import BattlePhase, BattleTiming
from battle.domain.utils import transition_to_phase

class CutinAnimationSystem(System):
    """
    CUTINフェーズの時間管理を行い、
    演出が終了したらEXECUTINGフェーズへ遷移させる。
    """

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        flow = entities[0][1]['battleflow']

        if flow.current_phase != BattlePhase.CUTIN:
            return

        # タイマー更新
        flow.phase_timer -= dt
        
        # 進行度更新
        max_time = BattleTiming.CUTIN_ANIMATION
        elapsed = max(0.0, max_time - flow.phase_timer)
        flow.cutin_progress = min(1.0, elapsed / max_time)
        
        # 時間経過で次のフェーズ（実行）へ
        if flow.phase_timer <= 0:
            transition_to_phase(flow, BattlePhase.EXECUTING)
            flow.cutin_progress = 1.0