"""バトル状態管理システム（統一された敗北判定システム）"""

from core.ecs import System
from components.battle_flow import BattleFlowComponent
from battle.constants import BattlePhase, TeamType

class BattleStatusSystem(System):
    """バトル状態管理システム（勝敗判定など）"""
    
    def update(self, dt: float = 0.016):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        if flow.current_phase == BattlePhase.GAME_OVER:
            return

        player_alive = False
        enemy_alive = False

        for _, components in self.world.entities.items():
            team = components.get('team')
            defeated = components.get('defeated')
            # チーム情報があり、敗北していない場合は生存扱い
            if not team:
                continue
            
            if defeated and defeated.is_defeated:
                continue

            if team.team_type == TeamType.PLAYER:
                player_alive = True
            elif team.team_type == TeamType.ENEMY:
                enemy_alive = True

        if not player_alive:
            flow.winner = "エネミー"
            flow.current_phase = BattlePhase.GAME_OVER
        elif not enemy_alive:
            flow.winner = "プレイヤー"
            flow.current_phase = BattlePhase.GAME_OVER
