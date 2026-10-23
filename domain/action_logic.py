# domain/action_logic.py
"""2層「Action（行動形式）」のデータ駆動型振る舞いロジック。

Action は「動作フォーム・リスク・リターン」のみを担う。
- 射撃（撃つ/狙い撃ち）: 事前予約 & 性格による敵部位選定を確定
- 格闘（殴る/我武者羅）: 直前選定 & 最前線の敵部位選定を確定
- 非攻撃（支援/妨害等）: ターゲットは技側（domain/skills.py）に委譲
"""
import dataclasses
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple, Union

from domain.constants import GaugeStatus, ActionType, TargetRule, TargetTiming


@dataclass(frozen=True)
class OffensiveBonuses:
    """行動形式による攻撃側の能力補正"""
    success: int = 0  # 成功度への加算値
    attack: int = 0   # 攻撃力への加算値


@dataclass(frozen=True)
class ActionDefinition:
    """行動形式（撃つ・殴る 等）の振る舞いを保持するデータクラス"""
    name: str = ""
    time_modifier: float = 1.0
    # 射撃・格闘はここで確定。非攻撃系の行動形式は None（技側へ委ねる）
    fixed_target_timing: Optional[TargetTiming] = None
    fixed_target_rule: Optional[TargetRule] = None
    # (自分の機動, 自分の防御) -> OffensiveBonuses
    offensive_bonus_fn: Callable[[int, int], OffensiveBonuses] = field(
        default=lambda mobility, defense: OffensiveBonuses()
    )
    defensive_penalty_fn: Callable[[GaugeStatus], Tuple[bool, bool, bool]] = field(
        default=lambda gauge_status: (False, False, False)
    )
    is_implemented: bool = True


# 各行動形式（Action）の定義テーブル（手書きでの name 二重定義を排除）
_RAW_ACTION_DEFINITIONS: Dict[ActionType, ActionDefinition] = {
    # 射撃系: 事前予約 & 性格による敵部位選定を確定
    ActionType.SHOOT: ActionDefinition(
        time_modifier=0.8,
        fixed_target_timing=TargetTiming.ON_CHARGE,
        fixed_target_rule=TargetRule.ENEMY_BY_PERSONALITY,
    ),
    ActionType.AIMED_SHOT: ActionDefinition(
        fixed_target_timing=TargetTiming.ON_CHARGE,
        fixed_target_rule=TargetRule.ENEMY_BY_PERSONALITY,
        offensive_bonus_fn=lambda mobility, defense: OffensiveBonuses(success=int(defense * 0.50)),
        defensive_penalty_fn=lambda gauge_status: (False, True, False) if gauge_status == GaugeStatus.CHARGING else (False, False, False),
    ),
    # 格闘系: 直前選定 & 最前線の敵部位選定を確定
    ActionType.STRIKE: ActionDefinition(
        fixed_target_timing=TargetTiming.ON_EXECUTE,
        fixed_target_rule=TargetRule.CLOSEST_ENEMY,
        offensive_bonus_fn=lambda mobility, defense: OffensiveBonuses(success=int(mobility * 0.25)),
        defensive_penalty_fn=lambda gauge_status: (True, False, False) if gauge_status == GaugeStatus.CHARGING else (False, False, False),
    ),
    ActionType.RECKLESS: ActionDefinition(
        fixed_target_timing=TargetTiming.ON_EXECUTE,
        fixed_target_rule=TargetRule.CLOSEST_ENEMY,
        offensive_bonus_fn=lambda mobility, defense: OffensiveBonuses(
            attack=int(mobility * 0.25) + int(defense * 0.25)
        ),
        defensive_penalty_fn=lambda gauge_status: (True, True, True) if gauge_status in (GaugeStatus.CHARGING, GaugeStatus.COOLDOWN) else (False, False, False),
    ),
    # 非攻撃系: ターゲットは技側へ委譲（fixed_* = None）
    ActionType.DISRUPT: ActionDefinition(),
    ActionType.SUPPORT: ActionDefinition(),
    ActionType.COVER: ActionDefinition(),
    ActionType.SELF_DEFENSE: ActionDefinition(),
    ActionType.HEAL: ActionDefinition(),
    ActionType.RECOVER: ActionDefinition(),
    ActionType.TRAP: ActionDefinition(),
    ActionType.PLANT: ActionDefinition(is_implemented=False),
}

# name は ActionType.value（日本語名）から自動注入（二重管理を排除しつつ外部からの .name 参照も保護）
ACTION_DEFINITIONS: Dict[ActionType, ActionDefinition] = {
    at: dataclasses.replace(defn, name=at.value)
    for at, defn in _RAW_ACTION_DEFINITIONS.items()
}

_DEFAULT_UNKNOWN = ActionDefinition(name="未定義", is_implemented=False)


def get_action_definition(action_type: Union[ActionType, str, None]) -> ActionDefinition:
    """指定された行動形式の振る舞い・定義を取得する（未定義は未実装として返す）"""
    at = ActionType.from_key(action_type)
    if at is None:
        return _DEFAULT_UNKNOWN
    return ACTION_DEFINITIONS.get(at, _DEFAULT_UNKNOWN)