"""バトル状態管理システム（統一された敗北判定システム）"""

from core.ecs import System
from battle.constants import BattlePhase, TeamType
from battle.domain.battle_helper import get_battle_state

class BattleStatusSystem(System):
    """バトル状態管理システム（勝敗判定など）"""
    
    def update(self, dt: float = 0.016):
        context, flow = get_battle_state(self.world)
        if not flow or flow.current_phase == BattlePhase.GAME_OVER:
            return

        player_leader_alive = False
        enemy_leader_alive = False

        for eid, comps in self.world.get_entities_with_components('team', 'defeated'):
            team = comps['team']
            if team.is_leader:
                is_alive = not comps['defeated'].is_defeated
                if team.team_type == TeamType.PLAYER:
                    player_leader_alive = is_alive
                elif team.team_type == TeamType.ENEMY:
                    enemy_leader_alive = is_alive

        if not player_leader_alive:
            flow.winner = "エネミー"
            flow.current_phase = BattlePhase.GAME_OVER
        elif not enemy_leader_alive:
            flow.winner = "プレイヤー"
            flow.current_phase = BattlePhase.GAME_OVER