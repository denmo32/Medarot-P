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

        gauge_entities = self.world.get_entities_with_components('gauge', 'defeated')

        # 1. まず行動選択待ち（ACTION_CHOICE）状態のエンティティを確実に待機列に追加
        # これにより、未処理の行動選択待ちがいる場合は時間を進めないようにする
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            gauge = comps['gauge']
            
            if gauge.status == gauge.ACTION_CHOICE:
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
            
            # ACTION_CHOICEはパス1で処理済み
            
            if gauge.status == gauge.CHARGING:
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
                    
                    # クールダウン完了で即座に待機列へ（同フレーム内のTurnSystemで処理可能にする）
                    if eid not in context.waiting_queue:
                        context.waiting_queue.append(eid)