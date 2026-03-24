"""ターン開始管理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import TeamType, GaugeStatus, BattlePhase
from battle.mechanics.flow import FlowMechanics, PhaseTransition


class TurnSystem(BattleSystemBase):
    """ターン開始とプレイヤー/エネミーの判定"""

    def update(self, dt: float):
        context = self.context
        flow = self.flow

        if not context or flow.current_phase != BattlePhase.IDLE or not context.waiting_queue:
            return

        eid = context.waiting_queue[0]
        comps = self.world.try_get_entity(eid)

        # エンティティが存在しない、または機能停止している場合はキューから削除
        defeated = comps.get('defeated') if comps else None
        if not comps or (defeated and defeated.is_defeated):
            context.waiting_queue.pop(0)
            return

        gauge = comps['gauge']
        team = comps['team']

        if gauge.status == GaugeStatus.ACTION_CHOICE:
            context.current_turn_entity_id = eid
            if team.team_type == TeamType.PLAYER:
                FlowMechanics.apply_transition(self.world, PhaseTransition(next_phase=BattlePhase.INPUT))
            else:
                FlowMechanics.apply_transition(self.world, PhaseTransition(next_phase=BattlePhase.ENEMY_TURN))
