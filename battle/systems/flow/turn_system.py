"""ターン開始管理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from domain.constants import TeamType, GaugeStatus
from battle.constants import BattlePhase
from domain.flow_logic import PhaseTransition


class TurnSystem(BattleSystemBase):
    """ターン開始とプレイヤー/エネミーの判定"""

    def update(self, dt: float):
        if not self.is_ready(BattlePhase.IDLE):
            return

        context = self.context
        if not context.waiting_queue:
            return

        eid = context.waiting_queue[0]
        comps = self.world.try_get_entity(eid)

        # エンティティが存在しない、または機能停止している場合はキューから削除
        defeated = comps.get('defeated') if comps else None
        if not comps or (defeated and defeated.is_defeated):
            self.remove_from_queue(eid)
            return

        gauge = comps['gauge']
        team = comps['team']

        if gauge.status == GaugeStatus.ACTION_CHOICE:
            context.current_turn_entity_id = eid
            if team.team_type == TeamType.PLAYER:
                self.apply_transition(PhaseTransition(next_phase=BattlePhase.INPUT))
            else:
                self.apply_transition(PhaseTransition(next_phase=BattlePhase.ENEMY_TURN))

