"""ATBゲージ更新システム"""

from core.ecs import System
from battle.constants import GaugeStatus, BattlePhase
from battle.service.flow_service import get_battle_state

class GaugeSystem(System):
    """ATBゲージの進行管理、および待機キューへの追加を担当。"""

    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not context or not flow: 
            return

        # 演出中やメッセージ表示中は時間が止まる
        if flow.current_phase != BattlePhase.IDLE:
            return

        gauge_entities = self.world.get_entities_with_components('gauge', 'defeated')

        # 1. 待機列（ACTION_CHOICE状態）の更新
        self._update_waiting_queue(gauge_entities, context)

        # 誰かが行動待機中（入力を待っているか、行動開始を待っている）の場合は、ゲージ進行を停止させる（ウェイト式ATB）
        if context.waiting_queue:
            return

        # 2. ゲージの進捗加算
        self._advance_gauges(gauge_entities, dt)

    def _update_waiting_queue(self, gauge_entities, context):
        """行動選択可能になったエンティティをキューに追加"""
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: 
                continue
            if comps['gauge'].status == GaugeStatus.ACTION_CHOICE:
                if eid not in context.waiting_queue:
                    context.waiting_queue.append(eid)

    def _advance_gauges(self, gauge_entities, dt):
        """時間経過によるゲージの更新"""
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: 
                continue
            
            gauge = comps['gauge']
            
            # 状態異常：停止
            if gauge.stop_timer > 0:
                gauge.stop_timer = max(0.0, gauge.stop_timer - dt)
                continue
            
            if gauge.status == GaugeStatus.CHARGING:
                gauge.progress += dt / gauge.charging_time * 100.0
                if gauge.progress >= 100.0:
                    gauge.progress = 100.0
                    # チャージ完了した瞬間に待機列へ
                    if eid not in self.world.entities[0]['battlecontext'].waiting_queue:
                        self.world.entities[0]['battlecontext'].waiting_queue.append(eid)
            
            elif gauge.status == GaugeStatus.COOLDOWN:
                gauge.progress += dt / gauge.cooldown_time * 100.0
                if gauge.progress >= 100.0:
                    # 冷却完了でコマンド入力待ちへ
                    gauge.progress = 0.0
                    gauge.status = GaugeStatus.ACTION_CHOICE
                    gauge.part_targets = {} 
                    gauge.selected_action = None
                    gauge.selected_part = None