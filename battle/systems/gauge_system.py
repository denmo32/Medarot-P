"""ATBゲージ更新システム"""

from core.ecs import System
from components.battle_flow import BattleFlowComponent
from battle.constants import GaugeStatus, BattlePhase

class GaugeSystem(System):
    """ATBゲージの進行管理のみを担当"""
    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        # IDLE状態以外（演出中や入力中）はゲージ更新を停止
        if flow.current_phase != BattlePhase.IDLE:
            return

        gauge_entities = self.world.get_entities_with_components('gauge', 'defeated')

        # 1. まず行動選択待ち（ACTION_CHOICE）状態のエンティティを確実に待機列に追加
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            gauge = comps['gauge']
            
            if gauge.status == GaugeStatus.ACTION_CHOICE:
                if eid not in context.waiting_queue:
                    context.waiting_queue.append(eid)

        # 2. 待機列に誰かいる場合（行動選択待ち、またはチャージ完了待ち）は
        # 他の機体のゲージ進行を停止する（ウェイト式）
        if context.waiting_queue:
            return

        # 3. ゲージ進行処理
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            gauge = comps['gauge']
            
            # 状態異常：停止の処理
            if gauge.stop_timer > 0:
                gauge.stop_timer = max(0.0, gauge.stop_timer - dt)
                continue # 停止中はゲージが一切進まない
            
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
                    
                    if eid not in context.waiting_queue:
                        context.waiting_queue.append(eid)