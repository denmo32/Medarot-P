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
    def resolve_indicator_transition(
        event_action_type: str,
        attacker_name: str,
        attack_trait: str,
        attack_skill_type: str
    ) -> PhaseTransition:
        """
        ターゲット指示演出終了後の、次のフェーズと付随するログを決定する
        
        Args:
            event_action_type: イベントのアクション種別
            attacker_name: 攻撃者の名前
            attack_trait: 攻撃パーツの特性
            attack_skill_type: 攻撃パーツのスキル種別
        
        Returns:
            フェーズ遷移情報
        """
        if event_action_type != ActionType.ATTACK:
            return PhaseTransition(next_phase=BattlePhase.EXECUTING)

        # 攻撃の場合の宣言ログ構築
        trait_text, skill_name = "", "攻撃"

        if attack_trait:
            trait_text = f" {attack_trait}！"
            skill_name = SkillRegistry.get(attack_skill_type).name

        log = LogBuilder.get_attack_declaration(attacker_name, skill_name, trait_text)

        return PhaseTransition(
            next_phase=BattlePhase.ATTACK_DECLARATION,
            logs=[log]
        )
