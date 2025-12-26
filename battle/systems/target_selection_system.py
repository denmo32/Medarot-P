"""ターゲット選定システム"""

from core.ecs import System
from battle.ai.personality import get_personality

class TargetSelectionSystem(System):
    """性格に基づき、各パーツの攻撃対象を事前に決定する"""

    def update(self, dt: float):
        # 行動選択待ち状態かつ、まだターゲットが決まっていないエンティティを処理
        for eid, comps in self.world.get_entities_with_components('gauge', 'medal', 'defeated'):
            if comps['defeated'].is_defeated: continue
            
            gauge = comps['gauge']
            if gauge.status == gauge.ACTION_CHOICE and not gauge.part_targets:
                personality = get_personality(comps['medal'].personality_id)
                gauge.part_targets = personality.select_targets(self.world, eid)