"""ダメージ処理システム"""

from core.ecs import System

class DamageSystem(System):
    """DamageEventComponentを監視し、実際のHP減算、状態異常適用を行う"""

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext')
        if not entities: return

        # DamageEventComponentを持つターゲットを探す
        for target_id, comps in self.world.get_entities_with_components('damageevent', 'partlist', 'gauge'):
            event = comps['damageevent']
            
            # 対象パーツのHPを削る
            part_id = comps['partlist'].parts.get(event.target_part)
            if part_id:
                health = self.world.entities[part_id]['health']
                health.hp = max(0, health.hp - event.damage)
                
                # 状態異常：停止の適用
                if event.stop_duration > 0:
                    comps['gauge'].stop_timer = max(comps['gauge'].stop_timer, event.stop_duration)

            # 処理が終わったらイベントを削除
            self.world.remove_component(target_id, 'damageevent')