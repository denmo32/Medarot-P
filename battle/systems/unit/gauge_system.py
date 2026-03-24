"""ATB ゲージ更新システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.gauge_mechanics import GaugeMechanics
from battle.mechanics.action import ActionMechanics
from battle.mechanics.flow import PhaseTransition

class GaugeSystem(BattleSystemBase):
    """ATB ゲージの進行管理、および状態異常のカウントダウンを担当"""

    def update(self, dt: float):
        # バトルが停止中（ログ表示中や演出中）はゲージを進めない
        if not self.query.context or not self.query.flow or self.query.flow.current_phase != BattlePhase.IDLE:
            return

        active_entities = [
            (eid, comps) for eid, comps in self.world.get_entities_with_components('gauge', 'defeated')
            if not comps['defeated'].is_defeated
        ]

        # 1. 状態異常の更新
        for _, comps in active_entities:
            gauge = comps['gauge']
            if gauge.active_effects:
                gauge.active_effects = GaugeMechanics.get_updated_effects(gauge.active_effects, dt)

        # 2. 中断判定とゲージ進行
        # 誰かが行動待機中の場合は、時間は進めるがゲージ増加は行わない
        time_step = 0.0 if self.query.context.waiting_queue else dt

        for eid, comps in active_entities:
            gauge = comps['gauge']

            # 行動の継続妥当性を検証（パーツ破壊チェックなど）
            interruption = ActionMechanics.validate_action_continuity(self.query, eid)
            if not interruption.is_valid:
                self.command.apply_gauge_reset(eid, interruption.reset_data)
                self.command.manage_queue(eid, False)
                self.command.apply_phase_transition(PhaseTransition(BattlePhase.LOG_WAIT, logs=[interruption.message]))
                # ログ表示フェーズに入るため、このフレームの処理を打ち切る
                return

            # ゲージ進行計算
            summary = GaugeMechanics.calculate_tick(gauge, time_step)

            # ゲージ値の更新
            gauge.progress = summary.new_progress

            # 放熱完了のチェックとリセット
            if summary.is_cooldown_finished:
                reset = ActionMechanics.get_choice_reset_data()
                self.command.apply_gauge_reset(eid, reset)
                # リセット後は待機列に入る必要がない
                self.command.manage_queue(eid, False)
            else:
                # 充填完了、または行動選択待ちならキューに追加
                self.command.manage_queue(eid, summary.should_be_in_queue)
