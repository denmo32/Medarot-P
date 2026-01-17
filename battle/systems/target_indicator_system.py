"""ターゲット演出管理システム"""

from core.ecs import System
from battle.constants import BattlePhase

class TargetIndicatorSystem(System):
    """
    TARGET_INDICATIONフェーズの時間管理を行い、
    時間が経過したらEXECUTINGフェーズへ遷移させる。
    """

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        flow = entities[0][1]['battleflow']

        if flow.current_phase != BattlePhase.TARGET_INDICATION:
            return

        # タイマー更新
        flow.phase_timer -= dt
        
        # 時間経過で次のフェーズへ
        if flow.phase_timer <= 0:
            flow.current_phase = BattlePhase.EXECUTING
            flow.phase_timer = 0.0