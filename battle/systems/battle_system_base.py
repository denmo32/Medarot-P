"""バトル系システムの基底クラス

BattleQuery（取得専用）と BattleCommand（副作用専用）を使用して、
システム間で共通操作を共有する。
"""

from core.ecs import System
from battle.systems.battle_query import BattleQuery
from battle.systems.battle_command import BattleCommand


class BattleSystemBase(System):
    """
    バトルシステム共通の基底クラス。

    BattleQuery と BattleCommand を経由して、バトル状態へのアクセスと操作を提供する。
    CQRS パターンにより、「取得のみ行う処理」と「副作用を起こす処理」を型レベルで区別できる。

    使用例:
        class GaugeSystem(BattleSystemBase):
            def update(self, dt: float):
                # 取得のみ (query)
                if self.query.flow.current_phase != BattlePhase.IDLE:
                    return
                # 副作用 (command)
                self.command.apply_gauge_reset(eid, reset_data)
    """

    def __init__(self, world):
        super().__init__(world)
        self.query = BattleQuery(world)
        self.command = BattleCommand(world)
