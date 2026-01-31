"""ダメージ処理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from components.battle_component import DamageEventComponent

class DamageSystem(BattleSystemBase):
    """DamageEventComponentを監視し、実際のHP減算、状態異常適用を行う"""

    def update(self, dt: float):
        context, _ = self.battle_state
        if not context: return

        for target_id, comps in self.world.get_entities_with_components('damageevent', 'partlist', 'gauge'):
            event: DamageEventComponent = comps['damageevent']
            
            # HP減算
            part_id = comps['partlist'].parts.get(event.target_part)
            p_comps = self.world.try_get_entity(part_id)
            if p_comps and 'health' in p_comps:
                health = p_comps['health']
                health.hp = max(0, health.hp - event.damage)
                
            # 状態異常の追加 (StatusEffect)
            if event.added_effects:
                gauge = comps['gauge']
                for new_effect in event.added_effects:
                    gauge.active_effects.append(new_effect)

            self.world.remove_component(target_id, 'damageevent')