"""バトル系システムの基底クラス

BattleStateAccessor を使用して、システム間で共通操作を共有する。
"""

from core.ecs import System
from battle.systems.battle_state_accessor import BattleStateAccessor


class BattleSystemBase(System):
    """
    バトルシステム共通の基底クラス。
    
    BattleStateAccessor を経由して、バトル状態へのアクセスと操作を提供する。
    
    使用例:
        class GaugeSystem(BattleSystemBase):
            def update(self, dt: float):
                if self.state.flow.current_phase != BattlePhase.IDLE:
                    return
                # 処理...
    """

    def __init__(self, world):
        super().__init__(world)
        self.state = BattleStateAccessor(world)
