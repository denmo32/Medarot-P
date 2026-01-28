"""ATBゲージ更新システム"""

from core.ecs import System
from battle.constants import GaugeStatus, BattlePhase
from battle.mechanics.flow import get_battle_state
from battle.mechanics.action import ActionMechanics
from battle.mechanics.status import StatusRegistry

class GaugeSystem(System):
    """ATBゲージ進行と状態異常（StatusEffect）の更新を担当"""

    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not context or not flow: return

        if flow.current_phase != BattlePhase.IDLE:
            return

        gauge_entities = self.world.get_entities_with_components('gauge', 'defeated')

        # 1. 中断チェック
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            if not ActionMechanics.validate_action_continuity(self.world, eid, context, flow):
                if flow.current_phase == BattlePhase.LOG_WAIT:
                    return

        # 2. 待機キュー更新
        self._update_waiting_queue(gauge_entities, context)
        if context.waiting_queue:
            return

        # 3. ゲージ・状態異常更新
        self._advance_gauges(gauge_entities, context, dt)

    def _update_waiting_queue(self, gauge_entities, context):
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            if comps['gauge'].status == GaugeStatus.ACTION_CHOICE:
                if eid not in context.waiting_queue:
                    context.waiting_queue.append(eid)

    def _advance_gauges(self, gauge_entities, context, dt):
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            gauge = comps['gauge']
            
            # --- Strategyパターンによる状態異常処理 ---
            can_charge = True
            
            # リストをコピーしてループ（削除対策）
            for effect in gauge.active_effects[:]:
                behavior = StatusRegistry.get(effect.type_id)
                
                # 毎フレーム処理
                behavior.on_tick(effect, gauge, dt)
                
                # 行動阻害判定
                if not behavior.can_charge(effect):
                    can_charge = False
                
                # 期限切れ削除
                if effect.duration <= 0:
                    gauge.active_effects.remove(effect)
            
            if not can_charge:
                continue
            # ------------------------------------

            if gauge.status == GaugeStatus.CHARGING:
                gauge.progress += dt / gauge.charging_time * 100.0
                if gauge.progress >= 100.0:
                    gauge.progress = 100.0
                    if eid not in context.waiting_queue:
                        context.waiting_queue.append(eid)
            
            elif gauge.status == GaugeStatus.COOLDOWN:
                gauge.progress += dt / gauge.cooldown_time * 100.0
                if gauge.progress >= 100.0:
                    gauge.progress = 0.0
                    gauge.status = GaugeStatus.ACTION_CHOICE
                    gauge.part_targets = {} 
                    gauge.selected_action = None
                    gauge.selected_part = None
                    if eid not in context.waiting_queue:
                        context.waiting_queue.append(eid)