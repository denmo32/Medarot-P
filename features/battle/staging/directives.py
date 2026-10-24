# features/battle/staging/directives.py
"""戦闘シーケンスの指示（Directive）および待機条件（Await）の定義。"""
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple, TYPE_CHECKING
from domain.constants import PartType

if TYPE_CHECKING:
    from features.battle.simulation.entities.commands import ExecutionReport
    from features.battle.simulation.entities.part import Part
    from features.battle.simulation.entities.robot import Robot


# ==============================================================================
# 即時指示 (Action Directives)
# ==============================================================================

class Directive:
    """戦闘シーケンス内で発行される即時指示の基底クラス"""
    pass


@dataclass(frozen=True)
class ShowLog(Directive):
    messages: List[str]


@dataclass(frozen=True)
class StartRadar(Directive):
    attacker_index: int
    target_index: int


@dataclass(frozen=True)
class ClearRadar(Directive):
    pass


@dataclass(frozen=True)
class StartCutin(Directive):
    actor: 'Robot'
    target: 'Robot'
    part: Optional['Part']
    report: 'ExecutionReport'


@dataclass(frozen=True)
class StageDamage(Directive):
    report: 'ExecutionReport'


@dataclass(frozen=True)
class AdvanceCutinPierce(Directive):
    report: 'ExecutionReport'


@dataclass(frozen=True)
class ClearCutin(Directive):
    pass


@dataclass(frozen=True)
class SetOpeningPopupVisible(Directive):
    visible: bool


# ==============================================================================
# 待機指示 (Await Directives) - 純粋データトークン
# ==============================================================================

class Await(Directive):
    """進行停止・待機条件を表すトークンの基底クラス"""
    pass


@dataclass
class AwaitTime(Await):
    remaining: float
    can_skip: bool = False


@dataclass(frozen=True)
class AwaitUserConfirm(Await):
    pass


@dataclass(frozen=True)
class AwaitHpAnimation(Await):
    pass


@dataclass(frozen=True)
class AwaitCutin(Await):
    pass


@dataclass(frozen=True)
class AwaitNextTurn(Await):
    pass


@dataclass(frozen=True)
class AwaitPlayerInput(Await):
    """プレイヤーのコマンド選択待機を表す純粋データトークン"""
    actor: 'Robot'
    preview_targets: dict
    selectable_mask: Tuple[bool, ...]