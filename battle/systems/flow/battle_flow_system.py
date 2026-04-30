"""バトルフロー管理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from domain.constants import TeamType, GaugeStatus
from battle.constants import BattlePhase
from domain.flow_logic import PhaseTransition


class BattleFlowSystem(BattleSystemBase):
    """バトルフェーズの遷移管理"""

    def update(self, dt: float):
        if not self.is_ready():
            return

        context = self.context
        flow = self.flow

        # 開始演出のトリガーチェック
        if flow.current_phase == BattlePhase.IDLE and not flow.is_opening_done:
            # プレイヤー機が全てコマンド決定済み（ACTION_CHOICE以外）かチェック
            player_units = self.world.get_entities_with_components('team', 'gauge')
            player_done = True
            player_exists = False
            for eid, comps in player_units:
                if comps['team'].team_type == TeamType.PLAYER:
                    player_exists = True
                    if comps['gauge'].status == GaugeStatus.ACTION_CHOICE:
                        player_done = False
                        break
            
            if player_exists and player_done:
                self._apply_transition(PhaseTransition(
                    next_phase=BattlePhase.OPENING_LOG,
                    logs=["合意と見てよろしいですね！？"]
                ))
                return

        # ポップアップ演出のタイマー管理
        if flow.current_phase == BattlePhase.OPENING_POPUP:
            flow.phase_timer -= dt
            if flow.phase_timer <= 0:
                flow.is_opening_done = True
                self._apply_transition(PhaseTransition(next_phase=BattlePhase.IDLE))
            return

        if flow.current_phase == BattlePhase.LOG_WAIT:
            if not context.battle_log:
                self._apply_transition(PhaseTransition(next_phase=BattlePhase.IDLE))

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
            flow.cutin_progress = 0.0

