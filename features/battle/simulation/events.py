"""戦闘のドメインイベントDTO。

ATBゲージ進行時に発生し、BattleDirector コルーチンへターンの発生を通知する
代数的データ型（ADT）。
"""
from dataclasses import dataclass
from typing import Union, TYPE_CHECKING
from domain.constants import TeamType

if TYPE_CHECKING:
    from .entities.commands import ExecutionReport
    from .entities.robot import Robot


@dataclass(frozen=True)
class PlayerInputRequiredEvent:
    """プレイヤーのコマンド選択が必要となったイベント"""
    actor: 'Robot'


@dataclass(frozen=True)
class ActionExecutedEvent:
    """機体の充填が完了し、行動が実行されたイベント"""
    actor: 'Robot'
    report: 'ExecutionReport'


@dataclass(frozen=True)
class BattleEndedEvent:
    """勝敗が決定したイベント"""
    winner: TeamType


# ATB更新時に発生しうるターンイベントの代数的データ型（ADT）
ATBTurnEvent = Union[PlayerInputRequiredEvent, ActionExecutedEvent, BattleEndedEvent]