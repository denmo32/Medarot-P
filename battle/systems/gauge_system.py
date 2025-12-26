"""ATBゲージ更新システム"""

from core.ecs import System

class GaugeSystem(System):
    """ATBゲージの進行管理のみを担当"""
    def update(self, dt: float):
        contexts = self.world.get_entities_with_components('battlecontext')
        if not contexts: return
        context = contexts[0][1]['battlecontext']

        # UI操作中やイベント待ちの間はゲージ更新を停止
        is_paused = len(context.waiting_queue) > 0 or context.waiting_for_input or context.waiting_for_action or context.game_over
        if is_paused: return

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