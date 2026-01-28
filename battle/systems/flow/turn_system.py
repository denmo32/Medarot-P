"""ターン開始管理システム"""

from core.ecs import System
from battle.constants import TeamType, GaugeStatus, BattlePhase
from battle.mechanics.flow import get_battle_state

class TurnSystem(System):
    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not context or flow.current_phase != BattlePhase.IDLE or not context.waiting_queue:
            return

        eid = context.waiting_queue[0]
        comps = self.world.entities.get(eid)
        if not comps:
            context.waiting_queue.pop(0)
            return

        gauge = comps['gauge']
        team = comps['team']

        if gauge.status == GaugeStatus.ACTION_CHOICE:
            context.current_turn_entity_id = eid
            if team.team_type == TeamType.PLAYER:
                flow.current_phase = BattlePhase.INPUT
            else:
                flow.current_phase = BattlePhase.ENEMY_TURN