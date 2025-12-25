"""バトル状態管理システム（統一された敗北判定システム）"""

from core.ecs import System

class BattleStatusSystem(System):
    """バトル状態管理システム（勝敗判定など）"""
    
    def update(self, dt: float = 0.016):
        contexts = self.world.get_entities_with_components('battlecontext')
        if not contexts: return
        context = contexts[0][1]['battlecontext']

        if context.game_over:
            return

        player_alive = False
        enemy_alive = False

        for _, components in self.world.entities.items():
            team = components.get('team')
            defeated = components.get('defeated')
            # チーム情報があり、敗北していない場合は生存扱い
            if not team:
                continue
            
            # DefeatedComponentがある場合、その状態をチェック
            if defeated and defeated.is_defeated:
                continue

            if team.team_type == "player":
                player_alive = True
            elif team.team_type == "enemy":
                enemy_alive = True

        if not player_alive:
            context.winner = "エネミー"
            context.game_over = True
        elif not enemy_alive:
            context.winner = "プレイヤー"
            context.game_over = True
