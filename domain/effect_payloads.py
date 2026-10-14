# domain/effect_payloads.py
"""行動結果が保持する「適用オブジェクト」の純粋な定義。
状態を変更せず、数値と対象データのみを保持する不変DTO。
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING
from domain.constants import PartType
from domain.traps import InstalledTrap

if TYPE_CHECKING:
    from domain.models import StatusEffect


@dataclass(frozen=True)
class AppliedEffect:
    """即時適用ペイロードの基底クラス"""
    pass


@dataclass(frozen=True)
class PartDamage(AppliedEffect):
    """主攻撃による被弾部位へのダメージ

    貫通ダメージや修復と同じ「適用オブジェクト」として扱うことで、
    主攻撃の状態更新も他の効果と同一の適用パイプライン（`EFFECT_HANDLERS`）に乗る。
    """

    part_type: PartType
    amount: int
    effective_damage: int = 0
    destroyed: bool = False


@dataclass(frozen=True)
class PartRepair(AppliedEffect):
    """対象機体の部位 HP を回復する"""

    part_type: PartType
    amount: int


@dataclass(frozen=True)
class PartRestore(AppliedEffect):
    """対象機体の破壊部位を復活させる"""

    part_type: PartType


@dataclass(frozen=True)
class TrapInstall(AppliedEffect):
    """フィールドへトラップを設置する"""

    trap: InstalledTrap


@dataclass(frozen=True)
class ApplyStatus(AppliedEffect):
    """機体に持続効果（状態異常・バフ・構え）を付与するペイロード"""

    effect: 'StatusEffect'
    target_self: bool = False  # True なら実行者、False なら対象者へ付与


@dataclass(frozen=True)
class PierceDamage(AppliedEffect):
    """主攻撃破壊時の貫通ダメージ"""

    part_type: PartType
    amount: int
    effective_damage: int = 0
    destroyed: bool = False
