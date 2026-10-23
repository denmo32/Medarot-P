# features/battle/entities/commands.py
"""バトルコマンド（指示・予約）のデータクラス (Command Pattern / DTO) および実行レポート。

機体の意志（予約状態）を表すため、エンティティ層に属します。
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, List, Optional, Tuple

from domain.constants import PartType
from domain.models import ActionResult

if TYPE_CHECKING:
    from domain.effect_payloads import PierceDamage
    from .part import Part
    from .robot import Robot


class ExecutionOutcome(Enum):
    """コマンド実行・自己診断の結果区分"""
    OK = auto()
    NO_ACTION = auto()
    SKIPPED = auto()
    PART_UNUSABLE = auto()
    PART_STOPPED = auto()
    ACTION_UNIMPLEMENTED = auto()
    TARGET_LOST = auto()
    RESERVED_PART_DESTROYED = auto()
    TRAP_DESTROYED = auto()  # トラップ被弾によるパーツ破壊を明示


@dataclass(frozen=True)
class BattleCommand:
    """1層 Command：バトルの実行指示を保持する基底データクラス"""
    actor: 'Robot'


@dataclass(frozen=True)
class ExecutionReport:
    """コマンド実行の結果を統一的に表すイミュータブルなレポート。"""
    outcome: ExecutionOutcome
    result: Optional[ActionResult] = None
    target: Optional['Robot'] = None
    intercepted_by: Optional['Robot'] = None
    pre_messages: List[str] = field(default_factory=list)
    result_messages: List[str] = field(default_factory=list)

    @property
    def has_pierce(self) -> bool:
        """この行動レポートに貫通ダメージが含まれるか"""
        return self.result.has_pierce if self.result else False

    @property
    def pierce_effect(self) -> Optional['PierceDamage']:
        return self.result.pierce_effect if self.result else None


@dataclass(frozen=True)
class SkipCommand(BattleCommand):
    """スキップ命令"""
    pass


@dataclass(frozen=True)
class PartCommand(BattleCommand):
    """パーツを使用する指示（攻撃・効果・支援等）のデータクラス"""
    part_type: PartType
    target_robot: Optional['Robot'] = None
    target_part: Optional[PartType] = None


def build_command_for_part(
    actor: 'Robot',
    part: 'Part',
    preview_target: Optional[Tuple['Robot', Optional[PartType]]] = None
) -> BattleCommand:
    """パーツの行動形式とプレビュー対象に基づいて適切なバトルコマンドを生成する。"""
    if not part.can_execute:
        return SkipCommand(actor)

    target_robot = preview_target[0] if preview_target else None
    target_part = preview_target[1] if preview_target else None

    return PartCommand(actor, part.part_type, target_robot, target_part)