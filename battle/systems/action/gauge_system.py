"""ATBゲージ更新システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import GaugeStatus, BattlePhase
from battle.mechanics.action import ActionMechanics
from battle.mechanics.status import StatusRegistry

class GaugeSystem(BattleSystemBase):
    """ATBゲージの進行管理、および状態異常のカウントダウンを担当"""

    def update(self, dt: float):
        context, flow = self.battle_state
        if not context or not flow or flow.current_phase != BattlePhase.IDLE:
            return

        gauge_entities = self.world.get_entities_with_components('gauge', 'defeated')

        # 1. 行動の継続妥当性を検証（パーツ破壊による中断など）
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            if not ActionMechanics.validate_action_continuity(self.world, eid, context, flow):
                if flow.current_phase == BattlePhase.LOG_WAIT: return

        # 2. 待機列（コマンド選択 or 行動実行待ち）の更新
        self._update_waiting_queue(gauge_entities, context)
        if context.waiting_queue: return

        # 3. ゲージの進行
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            self._process_entity_gauge(comps['gauge'], dt)

    def _update_waiting_queue(self, gauge_entities, context):
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            g = comps['gauge']
            # 選択待ち、または充填完了した機体をキューに追加
            if g.status == GaugeStatus.ACTION_CHOICE or (g.status == GaugeStatus.CHARGING and g.progress >= 100.0):
                if eid not in context.waiting_queue:
                    context.waiting_queue.append(eid)

    def _process_entity_gauge(self, gauge, dt):
        """個別エンティティのゲージ進行と状態異常処理"""
        can_charge = True
        
        # 状態異常の更新（逆順ループで安全な削除）
        for effect in reversed(gauge.active_effects):
            behavior = StatusRegistry.get(effect.type_id)
            behavior.on_tick(effect, gauge, dt)
            if not behavior.can_charge(effect):
                can_charge = False
            if effect.duration <= 0:
                gauge.active_effects.remove(effect)
        
        if not can_charge: return

        # ゲージ進行
        if gauge.status == GaugeStatus.CHARGING:
            gauge.progress = min(100.0, gauge.progress + (dt / gauge.charging_time * 100.0))
        elif gauge.status == GaugeStatus.COOLDOWN:
            gauge.progress += (dt / gauge.cooldown_time * 100.0)
            if gauge.progress >= 100.0:
                self._reset_to_choice(gauge)

    def _reset_to_choice(self, gauge):
        gauge.status = GaugeStatus.ACTION_CHOICE
        gauge.progress = 0.0
        gauge.part_targets = {} 
        gauge.selected_action = None
        gauge.selected_part = None