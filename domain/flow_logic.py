"""バトルフロー制御の純粋ロジック"""

from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from battle.constants import BattlePhase, ActionType
from domain.skill_logic import get_skill_behavior
from domain.log_logic import get_attack_declaration

@dataclass
class PhaseTransition:
    """遷移先の情報"""
    next_phase: str
    timer: float = 0.0
    actor_id: Optional[int] = None
    event_id: Optional[int] = None
    logs: List[str] = field(default_factory=list)
    clear_logs: bool = False

def resolve_indicator_transition(
    event_action_type: str,
    attacker_name: str,
    attack_trait: str,
    attack_skill_type: str
) -> PhaseTransition:
    """ターゲット指示演出終了後の、次のフェーズと付随するログを決定する"""
    if event_action_type != ActionType.ATTACK:
        return PhaseTransition(next_phase=BattlePhase.EXECUTING)

    # 攻撃の場合の宣言ログ構築
    trait_text, skill_name = "", "攻撃"

    if attack_trait:
        trait_text = f" {attack_trait}！"
        skill_name = get_skill_behavior(attack_skill_type).name

    log = get_attack_declaration(attacker_name, skill_name, trait_text)

    return PhaseTransition(
        next_phase=BattlePhase.ATTACK_DECLARATION,
        logs=[log]
    )
