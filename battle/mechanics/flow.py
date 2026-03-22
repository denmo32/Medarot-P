"""バトルフロー制御ロジック"""

from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field
from battle.constants import BattlePhase, ActionType
from battle.mechanics.skill import SkillRegistry
from battle.mechanics.log import LogBuilder
from core.ecs import World

@dataclass
class PhaseTransition:
    """遷移先の情報"""
    next_phase: str
    timer: float = 0.0
    actor_id: Optional[int] = None
    event_id: Optional[int] = None
    logs: List[str] = field(default_factory=list)
    clear_logs: bool = False

def get_battle_state(world: World) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    ワールドから BattleContext と BattleFlow を取得する。
    
    Args:
        world: ECS のワールドインスタンス
        
    Returns:
        (battle_context, battle_flow) のタプル。
        見つからない場合は (None, None)。
    """
    _, comps = world.get_first_entity('battlecontext', 'battleflow')
    if not comps:
        return None, None
    return comps['battlecontext'], comps['battleflow']

class FlowMechanics:
    """フェーズ遷移に関する判断ロジック"""

    @staticmethod
    def resolve_indicator_transition(world, event_eid: int) -> PhaseTransition:
        """ターゲット指示演出終了後の、次のフェーズと付随するログを決定する"""
        event_comps = world.try_get_entity(event_eid)
        if not event_comps or 'actionevent' not in event_comps:
            return PhaseTransition(next_phase=BattlePhase.EXECUTING)

        event = event_comps['actionevent']
        if event.action_type != ActionType.ATTACK:
            return PhaseTransition(next_phase=BattlePhase.EXECUTING)

        # 攻撃の場合の宣言ログ構築
        attacker_id = event.attacker_id
        attacker_comps = world.try_get_entity(attacker_id)
        if not attacker_comps:
            return PhaseTransition(next_phase=BattlePhase.EXECUTING)

        attacker_name = attacker_comps['medal'].nickname
        trait_text, skill_name = "", "攻撃"

        part_id = attacker_comps['partlist'].parts.get(event.part_type)
        part_comps = world.try_get_entity(part_id)
        if part_comps and 'attack' in part_comps:
            attack_comp = part_comps['attack']
            trait_text = f" {attack_comp.trait}！"
            skill_name = SkillRegistry.get(attack_comp.skill_type).name

        log = LogBuilder.get_attack_declaration(attacker_name, skill_name, trait_text)

        return PhaseTransition(
            next_phase=BattlePhase.ATTACK_DECLARATION,
            logs=[log]
        )
