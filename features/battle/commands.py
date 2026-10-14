"""バトルコマンド（指示）のデータクラス (Command Pattern / DTO) およびコマンド生成ヘルパー。

1層「Command（指示）」は、プレイヤーやAIが選ぶ実行予約（どのパーツを使う・スキップする）を表す。
実際の行動フォーム（撃つ・殴る 等）は 2層「Action（行動形式）」が担う。
"""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Tuple, List
from domain.constants import PartType, SkillKind
from domain.models import ActionResult

from .constants import ExecutionOutcome

if TYPE_CHECKING:
    from domain.effect_payloads import PierceDamage
    from .models import Robot, Part



@dataclass(frozen=True)
class BattleCommand:
    """1層 Command：バトルの実行指示を保持する基底データクラス"""
    actor: 'Robot'


@dataclass(frozen=True)
class ExecutionReport:
    """コマンド実行の結果を統一的に表すイミュータブルなレポート"""
    outcome: ExecutionOutcome
    result: Optional[ActionResult] = None
    target: Optional['Robot'] = None
    intercepted_by: Optional['Robot'] = None
    pre_messages: List[str] = field(default_factory=list)

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
    if not part.is_alive or not part.is_implemented:
        return SkipCommand(actor)

    target_robot = preview_target[0] if preview_target else None
    target_part = preview_target[1] if preview_target else None

    kind = part.skill_kind
    if kind in (SkillKind.ATTACK, SkillKind.EFFECT):
        return PartCommand(actor, part.part_type, target_robot, target_part)
    else:
        return SkipCommand(actor)
