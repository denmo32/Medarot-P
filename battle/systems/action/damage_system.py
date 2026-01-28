"""ダメージ処理システム"""

from core.ecs import System

class DamageSystem(System):
    """DamageEventComponentを監視し、実際のHP減算、状態異常適用を行う"""

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext')
        if not entities: return

        for target_id, comps in self.world.get_entities_with_components('damageevent', 'partlist', 'gauge'):
            event = comps['damageevent']
            
            # HP減算
            part_id = comps['partlist'].parts.get(event.target_part)
            if part_id:
                health = self.world.entities[part_id]['health']
                health.hp = max(0, health.hp - event.damage)
                
            # 状態異常の追加 (StatusEffect)
            if event.added_effects:
                gauge = comps['gauge']
                for new_effect in event.added_effects:
                    gauge.active_effects.append(new_effect)

            self.world.remove_component(target_id, 'damageevent')