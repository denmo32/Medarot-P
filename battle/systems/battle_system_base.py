"""バトル系システムの基底クラス"""

from core.ecs import System
from battle.mechanics.flow import get_battle_state

class BattleSystemBase(System):
    """BattleContextとBattleFlowへのアクセスを容易にする基底システム"""

    @property
    def battle_state(self):
        """(context, flow) のタプルを返す"""
        return get_battle_state(self.world)

    def get_context_and_flow(self):
        """内部更新用ヘルパー"""
        return self.battle_state