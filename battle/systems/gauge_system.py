"""ATBゲージ更新システム"""

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

        # GaugeComponentとPartHealthComponentを持つエンティティを更新
        for entity_id, components in self.world.entities.items():
            gauge_comp = components.get('gauge')
            part_health_comp = components.get('parthealth')

            if gauge_comp and part_health_comp:
                # 頭部HPが0の場合、機能停止（ロジックはシステム側で実行）
                if part_health_comp.head_hp <= 0:
                    part_health_comp.is_defeated = True
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
