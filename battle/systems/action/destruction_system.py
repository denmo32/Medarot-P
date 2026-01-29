"""破壊・機能停止判定システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import PartType

class DestructionSystem(BattleSystemBase):
    """各パーツのHPを監視し、部位破壊や機体の機能停止を判定する"""

    def update(self, dt: float):
        # 敗北判定が必要なエンティティ（Medabot本体）を走査
        for eid, comps in self.world.get_entities_with_components('partlist', 'defeated'):
            if comps['defeated'].is_defeated:
                continue

            # 頭部パーツのエンティティを取得
            head_id = comps['partlist'].parts.get(PartType.HEAD)
            head_comps = self.world.try_get_entity(head_id) if head_id is not None else None
            
            if head_comps and 'health' in head_comps:
                if head_comps['health'].hp <= 0:
                    comps['defeated'].is_defeated = True