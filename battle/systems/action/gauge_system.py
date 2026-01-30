"""ATBゲージ更新システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import GaugeStatus, BattlePhase
from battle.mechanics.gauge_mechanics import GaugeMechanics
from battle.mechanics.action import ActionMechanics
from battle.mechanics.flow import interrupt_to_log

class GaugeSystem(BattleSystemBase):
    """ATBゲージの進行管理、および状態異常のカウントダウンを担当"""

    def update(self, dt: float):
        if not self.context or not self.flow or self.flow.current_phase != BattlePhase.IDLE:
            return

        # 生存しているゲージ持ちエンティティを走査
        active_entities = [
            (eid, comps) for eid, comps in self.world.get_entities_with_components('gauge', 'defeated')
            if not comps['defeated'].is_defeated
        ]

        # 1. 行動の継続妥当性を検証（パーツ破壊による中断など）
        for eid, comps in active_entities:
            is_valid, message = GaugeMechanics.evaluate_interruption(self.world, eid)
            
            if not is_valid:
                self._handle_interruption(eid, comps['gauge'], message)
                if self.flow.current_phase != BattlePhase.IDLE:
                    return

        # 2. 待機列の更新
        for eid, comps in active_entities:
            should_wait = GaugeMechanics.should_be_in_waiting_queue(comps['gauge'])
            ActionMechanics.manage_waiting_queue(self.context.waiting_queue, eid, should_wait)
        
        # 誰かが入力待ち、または行動実行待機中であれば、ゲージ進行は一時停止
        if self.context.waiting_queue:
            return

        # 3. 各エンティティのゲージ進行処理
        for eid, comps in active_entities:
            gauge = comps['gauge']
            GaugeMechanics.process_tick(gauge, dt)
            
            # 放熱完了判定
            if GaugeMechanics.check_cooldown_complete(gauge):
                self._reset_to_choice(gauge)

    def _handle_interruption(self, entity_id, gauge, message):
        """行動中断の適用"""
        ActionMechanics.reset_to_cooldown(gauge, penalty_ratio=1.0)
        ActionMechanics.manage_waiting_queue(self.context.waiting_queue, entity_id, False)
        interrupt_to_log(self.context, self.flow, message)

    def _reset_to_choice(self, gauge):
        """放熱完了時の初期化"""
        gauge.status = GaugeStatus.ACTION_CHOICE
        gauge.progress = 0.0
        gauge.part_targets = {} 
        gauge.selected_action = None
        gauge.selected_part = None