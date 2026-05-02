"""破壊・機能停止判定システム"""

from battle.systems.base.battle_system_base import BattleSystemBase
from battle.constants import PartType


class DestructionSystem(BattleSystemBase):
    """部位破壊イベントを監視し、機体の機能停止を判定する"""

    def update(self, dt: float):
        # 部位破壊イベントを走査
        for event_eid, comps in self.world.get_entities_with_components('partdestroyedevent'):
            event = comps['partdestroyedevent']
            
            if event.part_type == PartType.HEAD:
                # 頭部が破壊されたら機能停止
                owner_comps = self.world.try_get_entity(event.owner_id)
                if owner_comps and 'defeated' in owner_comps:
                    owner_comps['defeated'].is_defeated = True

            # イベントエンティティの削除
            self.world.delete_entity(event_eid)
