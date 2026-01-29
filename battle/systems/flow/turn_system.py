"""ターン開始管理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import TeamType, GaugeStatus, BattlePhase

class TurnSystem(BattleSystemBase):
    def update(self, dt: float):
        context, flow = self.battle_state
        if not context or flow.current_phase != BattlePhase.IDLE or not context.waiting_queue:
            return

        eid = context.waiting_queue[0]
        comps = self.world.try_get_entity(eid)
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