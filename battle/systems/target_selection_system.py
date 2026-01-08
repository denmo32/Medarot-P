"""ターゲット選定システム"""

from core.ecs import System
from battle.ai.personality import get_personality
from components.battle_flow import BattleFlowComponent
from battle.constants import BattlePhase, GaugeStatus

class TargetSelectionSystem(System):
    """性格に基づき、各パーツの攻撃対象を事前に決定する"""

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        flow = entities[0][1]['battleflow']

        # IDLE状態のときのみターゲット選定更新を行う（演出中などに変更されないように）
        if flow.current_phase != BattlePhase.IDLE:
            return

        # 行動選択待ち（ACTION_CHOICE）状態かつ、まだターゲットが決まっていないエンティティを処理
        for eid, comps in self.world.get_entities_with_components('gauge', 'medal', 'defeated'):
            if comps['defeated'].is_defeated: continue
            
            gauge = comps['gauge']
            if gauge.status == GaugeStatus.ACTION_CHOICE and not gauge.part_targets:
                personality = get_personality(comps['medal'].personality_id)
                gauge.part_targets = personality.select_targets(self.world, eid)
