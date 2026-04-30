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
            context.waiting_queue.pop(0)
            return

        gauge = comps['gauge']
        team = comps['team']

        if gauge.status == GaugeStatus.ACTION_CHOICE:
            context.current_turn_entity_id = eid
            if team.team_type == TeamType.PLAYER:
                self._apply_transition(PhaseTransition(next_phase=BattlePhase.INPUT))
            else:
                self._apply_transition(PhaseTransition(next_phase=BattlePhase.ENEMY_TURN))

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

