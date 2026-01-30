"""ATBゲージ更新システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.gauge_mechanics import GaugeMechanics
from battle.mechanics.action import ActionMechanics
from battle.mechanics.flow import PhaseTransition

class GaugeSystem(BattleSystemBase):
    """ATBゲージの進行管理、および状態異常のカウントダウンを担当"""

    def update(self, dt: float):
        if not self.context or not self.flow or self.flow.current_phase != BattlePhase.IDLE:
            return

        active_entities = [
            (eid, comps) for eid, comps in self.world.get_entities_with_components('gauge', 'defeated')
            if not comps['defeated'].is_defeated
        ]

        # 1. 状態異常の更新
        for _, comps in active_entities:
            gauge = comps['gauge']
            gauge.active_effects = GaugeMechanics.get_updated_effects(gauge.active_effects, dt)

        # 2. 行動の継続妥当性を検証
        for eid, comps in active_entities:
            # 判断をMechanicsに委譲
            interruption = ActionMechanics.validate_action_continuity(self.world, eid)
            if not interruption.is_valid:
                # 副作用を適用
                self.apply_gauge_reset(eid, interruption.reset_data)
                self.manage_queue(eid, False)
                self.apply_phase_transition(PhaseTransition(BattlePhase.LOG_WAIT, logs=[interruption.message]))
                # ログ待ちに入った場合はこのフレームの他のゲージ処理は中断
                return

        # 3. 待機列の同期
        for eid, comps in active_entities:
            # ゲージ進行計算（副作用なしの問い合せ）
            summary = GaugeMechanics.calculate_tick(comps['gauge'], dt=0)
            self.manage_queue(eid, summary.should_be_in_queue)
        
        # 誰かが行動待機中ならゲージ進行は停止
        if self.context.waiting_queue:
            return

        # 4. ゲージ進行処理
        for eid, comps in active_entities:
            gauge = comps['gauge']
            summary = GaugeMechanics.calculate_tick(gauge, dt)
            
            # 値の更新
            gauge.progress = summary.new_progress
            
            # 放熱完了のチェックとリセット（副作用の実行）
            if summary.is_cooldown_finished:
                reset = ActionMechanics.get_choice_reset_data()
                self.apply_gauge_reset(eid, reset)