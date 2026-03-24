"""バトル系システムの基底クラス

ECS の World を直接操作することを基本とし、
頻繁にアクセスする Context と Flow へのショートカットのみを提供する。
"""

from core.ecs import System
from battle.mechanics.flow import get_battle_state


class BattleSystemBase(System):
    """
    バトルシステム共通の基底クラス。
    """
    @property
    def context(self):
        ctx, _ = get_battle_state(self.world)
        return ctx

    @property
    def flow(self):
        _, flow = get_battle_state(self.world)
        return flow
