"""ATBゲージ更新システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.gauge_mechanics import GaugeMechanics
from battle.mechanics.action import ActionMechanics
from battle.mechanics.flow import interrupt_to_log

class GaugeSystem(BattleSystemBase):
    """ATBゲージの進行管理、および状態異常のカウントダウンを担当"""

    def update(self, dt: float):
        if not self.context or not self.flow or self.flow.current_phase != BattlePhase.IDLE:
            return

        # 生存しているゲージ持ちエンティティを取得
        active_entities = [
            (eid, comps) for eid, comps in self.world.get_entities_with_components('gauge', 'defeated')
            if not comps['defeated'].is_defeated
        ]

        # 1. 状態異常のカウントダウン（純粋関数から新しいリストを受け取り適用）
        for _, comps in active_entities:
            gauge = comps['gauge']
            gauge.active_effects = GaugeMechanics.get_updated_effects(gauge.active_effects, dt)

        # 2. 行動の継続妥当性を検証
        for eid, comps in active_entities:
            is_valid, message = ActionMechanics.validate_action_continuity(self.world, eid)
            if not is_valid:
                self._handle_interruption(eid, comps['gauge'], message)
                if self.flow.current_phase != BattlePhase.IDLE:
                    return

        # 3. 待機列の同期
        for eid, comps in active_entities:
            summary = GaugeMechanics.get_tick_summary(comps['gauge'])
            self._manage_queue(eid, summary.should_be_in_queue)
        
        # 誰かが入力待ち、または行動実行待機中であれば、ゲージ進行は一時停止
        if self.context.waiting_queue:
            return

        # 4. ゲージ進行処理
        for eid, comps in active_entities:
            gauge = comps['gauge']
            new_progress, _ = GaugeMechanics.calculate_tick(gauge, dt)
            gauge.progress = new_progress
            
            # 放熱完了のチェックとリセット（副作用の実行）
            summary = GaugeMechanics.get_tick_summary(gauge)
            if summary.is_cooldown_finished:
                reset = ActionMechanics.get_choice_reset_data()
                gauge.status = reset.status
                gauge.progress = reset.progress
                if reset.clear_selection:
                    gauge.selected_action = None
                    gauge.selected_part = None
                    gauge.part_targets = {}

    def _manage_queue(self, entity_id: int, should_add: bool):
        queue = self.context.waiting_queue
        if should_add and entity_id not in queue:
            queue.append(entity_id)
        elif not should_add and entity_id in queue:
            queue.remove(entity_id)

    def _handle_interruption(self, entity_id, gauge, message):
        """行動中断の適用（副作用の実行）"""
        reset = ActionMechanics.get_cooldown_reset_data(gauge.progress, penalty_ratio=1.0)
        gauge.status = reset.status
        gauge.progress = reset.progress
        if reset.clear_selection:
            gauge.selected_action = None
            gauge.selected_part = None
            gauge.part_targets = {}
            
        self._manage_queue(entity_id, False)
        interrupt_to_log(self.context, self.flow, message)