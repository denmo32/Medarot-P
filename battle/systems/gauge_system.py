"""ATBゲージ更新システム"""

from core.ecs import System
from components.battle_flow import BattleFlowComponent

class GaugeSystem(System):
    """ATBゲージの進行管理のみを担当"""
    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        # IDLE状態以外（演出中や入力中）はゲージ更新を停止
        if flow.current_phase != BattleFlowComponent.PHASE_IDLE:
            return

        for eid, comps in self.world.get_entities_with_components('gauge', 'defeated'):
            gauge = comps['gauge']
            if comps['defeated'].is_defeated: continue
                
            if gauge.status == gauge.ACTION_CHOICE:
                if eid not in context.waiting_queue:
                    context.waiting_queue.append(eid)

            elif gauge.status == gauge.CHARGING:
                gauge.progress += dt / gauge.charging_time * 100.0
                if gauge.progress >= 100.0:
                    gauge.progress = 100.0
                    if eid not in context.waiting_queue:
                        context.waiting_queue.append(eid)
            
            elif gauge.status == gauge.COOLDOWN:
                gauge.progress += dt / gauge.cooldown_time * 100.0
                if gauge.progress >= 100.0:
                    gauge.progress = 0.0
                    gauge.status = gauge.ACTION_CHOICE
                    gauge.part_targets = {} # ターゲット選定をリセット