"""バトル状態管理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from domain.constants import TeamType
from battle.constants import BattlePhase
from domain.flow_logic import PhaseTransition


class BattleStatusSystem(BattleSystemBase):
    """勝敗判定とゲームオーバー管理"""

    def update(self, dt: float):
        flow = self.flow
        if not flow or flow.current_phase == BattlePhase.GAME_OVER:
            return

        # 勝敗判定はバトルフローが落ち着いた IDLE フェーズでのみ行う
        # これにより、カットイン演出・結果ログ・HPゲージアニメーションが
        # 全て完了してからゲームオーバー遷移がトリガーされる
        if flow.current_phase != BattlePhase.IDLE:
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
            self.apply_transition(PhaseTransition(next_phase=BattlePhase.GAME_OVER))
        elif not enemy_leader_alive:
            flow.winner = "プレイヤー"
            self.apply_transition(PhaseTransition(next_phase=BattlePhase.GAME_OVER))
