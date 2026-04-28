"""バトルフロー管理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase, TeamType, GaugeStatus
from battle.mechanics.flow import FlowMechanics, PhaseTransition


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
                FlowMechanics.apply_transition(self.world, PhaseTransition(
                    next_phase=BattlePhase.OPENING_LOG,
                    logs=["合意と見てよろしいですね！？"]
                ))
                return

        # ポップアップ演出のタイマー管理
        if flow.current_phase == BattlePhase.OPENING_POPUP:
            flow.phase_timer -= dt
            if flow.phase_timer <= 0:
                flow.is_opening_done = True
                FlowMechanics.apply_transition(self.world, PhaseTransition(next_phase=BattlePhase.IDLE))
            return

        if flow.current_phase == BattlePhase.LOG_WAIT:
            if not context.battle_log:
                FlowMechanics.apply_transition(self.world, PhaseTransition(next_phase=BattlePhase.IDLE))
