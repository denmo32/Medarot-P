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

        # リーダーの生存確認
        player_leader_alive = False
        enemy_leader_alive = False

        # 'team' と 'defeated' を持つエンティティのみを対象にする
        for eid, comps in self.world.get_entities_with_components('team', 'defeated'):
            team = comps['team']
            
            # リーダーである機体のみをチェック
            if team.is_leader:
                is_alive = not comps['defeated'].is_defeated
                
                if team.team_type == TeamType.PLAYER:
                    player_leader_alive = is_alive
                elif team.team_type == TeamType.ENEMY:
                    enemy_leader_alive = is_alive

        # リーダーが倒れたら勝敗決定
        if not player_leader_alive:
            flow.winner = "エネミー"
            flow.current_phase = BattlePhase.GAME_OVER
        elif not enemy_leader_alive:
            flow.winner = "プレイヤー"
            flow.current_phase = BattlePhase.GAME_OVER