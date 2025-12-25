"""ATBゲージ更新システム（統一された敗北判定システム）"""

from core.ecs import System
from components.battle import GaugeComponent

class GaugeSystem(System):
    """ATBゲージ更新システム"""
    def update(self, dt: float = 0.016):
        # バトルコンテキストを取得
        contexts = self.world.get_entities_with_components('battlecontext')
        if not contexts:
            return
        context = contexts[0][1]['battlecontext']

        # UI操作中やイベント待ちの間はゲージ更新を停止
        is_paused = len(context.waiting_queue) > 0 or context.waiting_for_input or context.waiting_for_action or context.game_over
        if is_paused:
            return

        # GaugeComponentとDefeatedComponentを持つエンティティを更新（統一システム）
        for entity_id, components in self.world.entities.items():
            gauge_comp = components.get('gauge')
            defeated = components.get('defeated')

            if not gauge_comp:
                continue
            
            # 敗北している場合は処理停止
            if defeated and defeated.is_defeated:
                continue
                
            # ゲージ更新ロジック
            if gauge_comp.status == GaugeComponent.ACTION_CHOICE:
                # 行動選択待ち状態になったらキューに追加
                if entity_id not in context.waiting_queue:
                    context.waiting_queue.append(entity_id)
            
            elif gauge_comp.status == GaugeComponent.CHARGING:
                # チャージ中
                gauge_comp.progress += dt / gauge_comp.charging_time * 100.0
                if gauge_comp.progress >= 100.0:
                    gauge_comp.progress = 100.0
                    # チャージ完了したら実行待ちキューへ
                    if entity_id not in context.waiting_queue:
                        context.waiting_queue.append(entity_id)
            
            elif gauge_comp.status == GaugeComponent.COOLDOWN:
                # クールダウン中
                gauge_comp.progress += dt / gauge_comp.cooldown_time * 100.0
                if gauge_comp.progress >= 100.0:
                    gauge_comp.progress = 0.0
                    gauge_comp.status = GaugeComponent.ACTION_CHOICE
                    # クールダウン完了で行動選択待ちへ
                    if entity_id not in context.waiting_queue:
                        context.waiting_queue.append(entity_id)
