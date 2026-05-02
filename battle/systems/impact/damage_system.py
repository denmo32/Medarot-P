"""ダメージ処理システム"""

from battle.systems.base.battle_system_base import BattleSystemBase
from components.battle_component import DamageEventComponent, PartDestroyedEventComponent


class DamageSystem(BattleSystemBase):
    """DamageEventComponent を監視し、実際の HP 減算、状態異常適用を行う"""

    def update(self, dt: float):
        context = self.context
        if not context:
            return

        for target_id, comps in self.world.get_entities_with_components('damageevent', 'partlist', 'gauge'):
            event: DamageEventComponent = comps['damageevent']

            # HP 減算
            part_id = self.get_part_entity_id(target_id, event.target_part)
            p_comps = self.world.try_get_entity(part_id)
            if p_comps and 'health' in p_comps:
                health = p_comps['health']
                old_hp = health.hp
                health.hp = max(0, health.hp - event.damage)

                # 部位破壊イベントの送出
                if old_hp > 0 and health.hp <= 0:
                    destroy_event = PartDestroyedEventComponent(
                        owner_id=target_id,
                        part_type=event.target_part
                    )
                    # 破壊イベントエンティティを作成
                    e_id = self.world.create_entity()
                    self.world.add_component(e_id, destroy_event)

            # 状態異常の追加 (StatusEffect)
            if event.added_effects:
                gauge = comps['gauge']
                for new_effect in event.added_effects:
                    gauge.active_effects.append(new_effect)

            self.world.remove_component(target_id, 'damageevent')
