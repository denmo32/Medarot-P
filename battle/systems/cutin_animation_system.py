"""カットイン演出管理システム"""

from core.ecs import System
from battle.constants import BattlePhase

class CutinAnimationSystem(System):
    """
    CUTINフェーズの時間管理を行い、
    演出が終了したらEXECUTINGフェーズへ遷移させる。
    実際の描画はRenderSystemが行うが、ここでは「演出が進行している」状態を担保する。
    """

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        flow = entities[0][1]['battleflow']

        if flow.current_phase != BattlePhase.CUTIN:
            return

        # タイマー更新
        flow.phase_timer -= dt
        
        # 進行度更新 (最大時間を1.5秒と仮定)
        max_time = 1.5
        elapsed = max(0.0, max_time - flow.phase_timer)
        flow.cutin_progress = min(1.0, elapsed / max_time)
        
        # 時間経過で次のフェーズ（実行）へ
        if flow.phase_timer <= 0:
            flow.current_phase = BattlePhase.EXECUTING
            flow.phase_timer = 0.0
            flow.cutin_progress = 1.0