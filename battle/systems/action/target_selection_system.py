"""ターゲット選定システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.mechanics.personality import PersonalityRegistry
from battle.constants import BattlePhase, GaugeStatus

class TargetSelectionSystem(BattleSystemBase):
    """性格に基づき、各パーツの攻撃対象を事前に決定する"""

    def update(self, dt: float):
        _, flow = self.battle_state
        if not flow or flow.current_phase != BattlePhase.IDLE:
            return

        # 行動選択待ち（ACTION_CHOICE）状態かつ、まだターゲットが決まっていないエンティティを処理
        for eid, comps in self.world.get_entities_with_components('gauge', 'medal', 'defeated'):
            if comps['defeated'].is_defeated: continue
            
            gauge = comps['gauge']
            if gauge.status == GaugeStatus.ACTION_CHOICE and not gauge.part_targets:
                # 性格振る舞いの取得はRegistryへ委譲
                personality = PersonalityRegistry.get(comps['medal'].personality_id)
                gauge.part_targets = personality.select_targets(self.world, eid)