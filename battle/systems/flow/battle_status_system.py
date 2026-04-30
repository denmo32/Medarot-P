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
            self._apply_transition(PhaseTransition(next_phase=BattlePhase.GAME_OVER))
        elif not enemy_leader_alive:
            flow.winner = "プレイヤー"
            self._apply_transition(PhaseTransition(next_phase=BattlePhase.GAME_OVER))

    # --- Local Helpers ---

    def _apply_transition(self, transition: PhaseTransition):
        flow = self.flow
        ctx = self.context
        if not flow: return
        flow.current_phase = transition.next_phase
        flow.phase_timer = transition.timer
        if transition.actor_id is not None: flow.active_actor_id = transition.actor_id
        if transition.event_id is not None: flow.processing_event_id = transition.event_id
        if transition.logs and ctx: ctx.battle_log.extend(transition.logs)
        if transition.next_phase == BattlePhase.IDLE:
            flow.processing_event_id = None
            flow.active_actor_id = None

