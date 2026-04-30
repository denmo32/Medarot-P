"""バトル系システムの基底クラス

ECS の World を直接操作することを基本とし、
頻繁にアクセスする Context と Flow へのショートカットのみを提供する。
"""

from typing import Optional, Dict, Any, List
from core.ecs import System
from battle.systems.utils.flow_handler import get_battle_state
from battle.constants import BattlePhase
from domain.flow_logic import PhaseTransition
from domain.combat_logic import LegsStats
from domain.constants import PartType


class BattleSystemBase(System):
    """
    バトルシステム共通の基底クラス。
    """
    @property
    def context(self):
        ctx, _ = get_battle_state(self.world)
        return ctx

    @property
    def flow(self):
        _, flow = get_battle_state(self.world)
        return flow

    def is_ready(self, required_phase: Optional[str] = None) -> bool:
        """
        システムが更新処理を実行できる状態かチェックする。
        """
        if not self.context or not self.flow:
            return False
        if required_phase and self.flow.current_phase != required_phase:
            return False
        return True

    def get_entity_name(self, entity_id: int) -> str:
        """エンティティの名前を取得する。"""
        comps = self.world.try_get_entity(entity_id)
        if comps and 'medal' in comps:
            return comps['medal'].nickname
        return "Unknown"

    def get_entity_comps(self, entity_id: int, *component_names: str) -> Optional[Dict[str, Any]]:
        """エンティティから指定されたコンポーネントを取得する。"""
        return self.world.try_get_components(entity_id, *component_names)

    def apply_transition(self, transition: PhaseTransition):
        """フェーズ遷移を適用する。"""
        flow = self.flow
        ctx = self.context
        if not flow: return
        
        flow.current_phase = transition.next_phase
        flow.phase_timer = transition.timer
        if transition.actor_id is not None: flow.active_actor_id = transition.actor_id
        if transition.event_id is not None: flow.processing_event_id = transition.event_id
        if transition.logs and ctx: ctx.battle_log.extend(transition.logs)
        
        if transition.next_phase == BattlePhase.IDLE:
            flow.processing_event_id = None
            flow.active_actor_id = None
            flow.cutin_progress = 0.0

    def remove_from_queue(self, eid: int):
        """待機キューからエンティティを削除する。"""
        if self.context and eid in self.context.waiting_queue:
            self.context.waiting_queue.remove(eid)

    def is_part_alive(self, eid: int, part_type: str) -> bool:
        """特定の部位が生存しているかチェックする。"""
        comps = self.world.try_get_entity(eid)
        if not comps or (comps.get('defeated') and comps['defeated'].is_defeated): return False
        pid = comps['partlist'].parts.get(part_type)
        if pid is None: return False
        p_comps = self.world.try_get_entity(pid)
        return bool(p_comps and 'health' in p_comps and p_comps['health'].hp > 0)

    def apply_gauge_reset(self, gauge, reset_data):
        """ゲージのリセット処理を適用する。"""
        gauge.status = reset_data.status
        gauge.progress = reset_data.progress
        if reset_data.clear_selection:
            gauge.selected_action = None
            gauge.selected_part = None
            gauge.part_targets = {}

    def get_legs_stats(self, eid: int) -> LegsStats:
        """脚部ステータスを取得する。"""
        comps = self.world.try_get_entity(eid)
        if comps and 'partlist' in comps:
            legs_id = comps['partlist'].parts.get(PartType.LEGS)
            if legs_id:
                l_comps = self.world.try_get_entity(legs_id)
                if l_comps and 'mobility' in l_comps:
                    return LegsStats(mobility=l_comps['mobility'].mobility, defense=l_comps['mobility'].defense)
        return LegsStats(0, 0)

    def get_alive_parts_hp(self, eid: int) -> Dict[str, int]:
        """生存している部位のHPを辞書で取得する。"""
        comps = self.world.try_get_entity(eid)
        if not comps or 'partlist' not in comps: return {}
        res = {}
        for pt, pid in comps['partlist'].parts.items():
            p_comps = self.world.try_get_entity(pid)
            if p_comps and 'health' in p_comps:
                hp = p_comps['health'].hp
                if hp > 0: res[pt] = hp
        return res

    def get_part_entity_id(self, owner_eid: int, part_type: str) -> Optional[int]:
        """機体の特定の部位のエンティティIDを取得する。"""
        owner_comps = self.world.try_get_entity(owner_eid)
        if not owner_comps or 'partlist' not in owner_comps:
            return None
        return owner_comps['partlist'].parts.get(part_type)

    def get_part_component(self, owner_eid: int, part_type: str, component_name: str) -> Optional[Any]:
        """機体の特定の部位のコンポーネントを取得する。"""
        part_eid = self.get_part_entity_id(owner_eid, part_type)
        if part_eid is None:
            return None
        part_comps = self.world.try_get_entity(part_eid)
        return part_comps.get(component_name) if part_comps else None
