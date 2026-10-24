"""戦闘シーケンスの進行待機条件（Await）の定義。"""
from dataclasses import dataclass
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from features.battle.simulation.entities.robot import Robot


class Await:
    """進行停止・待機条件を表す純粋データトークンの基底クラス"""
    pass


@dataclass
class AwaitTime(Await):
    """指定秒数の時間経過を待機する"""
    remaining: float
    can_skip: bool = False


@dataclass(frozen=True)
class AwaitUserConfirm(Await):
    """ユーザーの決定入力（OKキー / クリック）を待機する"""
    pass


@dataclass(frozen=True)
class AwaitHpAnimation(Await):
    """HPゲージ減少および破壊フェードの完了を待機する"""
    pass


@dataclass(frozen=True)
class AwaitCutin(Await):
    """カットイン演出の完了を待機する"""
    pass


@dataclass(frozen=True)
class AwaitNextTurn(Await):
    """ATBゲージの端到達（次の手番発生）を待機する"""
    pass


@dataclass(frozen=True)
class AwaitPlayerInput(Await):
    """プレイヤーのコマンド選択入力を待機する"""
    actor: 'Robot'
    preview_targets: dict
    selectable_mask: Tuple[bool, ...]