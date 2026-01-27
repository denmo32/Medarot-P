"""破壊・機能停止判定システム"""

from core.ecs import System
from battle.constants import PartType

class DestructionSystem(System):
    """各パーツのHPを監視し、部位破壊や機体の機能停止を判定する"""

    def update(self, dt: float):
        # 敗北判定が必要なエンティティ（Medabot本体）を走査
        for eid, comps in self.world.get_entities_with_components('partlist', 'defeated'):
            if comps['defeated'].is_defeated:
                continue

            # 頭部パーツのエンティティを取得
            head_id = comps['partlist'].parts.get(PartType.HEAD)
            if head_id is not None:
                head_health = self.world.entities[head_id].get('health')
                
                # 頭部HPが0なら機能停止
                if head_health and head_health.hp <= 0:
                    comps['defeated'].is_defeated = True