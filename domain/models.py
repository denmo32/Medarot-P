"""ドメインモデルのデータクラス定義"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass(frozen=True)
class PartData:
    """パーツデータを表す不変データクラス"""
    name: str
    skill: str
    trait: str
    hp: int
    attack: Optional[int]
    success: int
    mobility: int = 0
    defense: int = 0
    attribute: str = "undefined"

    @classmethod
    def from_dict(cls, data: dict) -> "PartData":
        """辞書から PartData インスタンスを生成する"""
        return cls(
            name=data.get("name", ""),
            skill=data.get("skill", ""),
            trait=data.get("trait", ""),
            hp=data.get("hp", 0),
            attack=data.get("attack"),
            success=data.get("success", 0),
            mobility=data.get("mobility", 0),
            defense=data.get("defense", 0),
            attribute=data.get("attribute", "undefined"),
        )


@dataclass(frozen=True)
class MedalData:
    """メダルデータを表す不変データクラス"""
    name: str
    nickname: str
    personality: str
    attribute: str

    @classmethod
    def from_dict(cls, data: dict) -> "MedalData":
        """辞書から MedalData インスタンスを生成する"""
        return cls(
            name=data.get("name", ""),
            nickname=data.get("nickname", ""),
            personality=data.get("personality", "random"),
            attribute=data.get("attribute", "undefined"),
        )

@dataclass
class StatusEffect:
    """汎用的な状態異常データ"""
    type_id: str             # "stop", "burn", "virus" 等
    duration: float          # 残り時間
    params: Dict[str, Any] = field(default_factory=dict) # 任意のパラメータ

@dataclass(frozen=True)
class CombatStats:
    """戦闘計算に使用するステータス値"""
    success: int
    attack: int
    tgt_mobility: int
    tgt_defense: int

@dataclass(frozen=True)
class DefensivePenalty:
    """ターゲット側の防御制限ペナルティ"""
    prevent_defense: bool = False
    force_hit: bool = False
    force_critical: bool = False

@dataclass(frozen=True)
class AttackParams:
    """攻撃側の計算パラメータ"""
    success: int
    attack: int
    part_attribute: str
    skill_type: str
    trait: str = ""

@dataclass(frozen=True)
class MedalParams:
    """メダルのパラメータ"""
    attribute: str

@dataclass(frozen=True)
class LegsStats:
    """脚部パーツのステータス"""
    mobility: int
    defense: int

@dataclass
class CombatResult:
    """戦闘計算の結果"""
    is_hit: bool
    is_critical: bool = False
    is_defense: bool = False
    damage: int = 0
    hit_part: Optional[str] = None
    added_effects: List[StatusEffect] = field(default_factory=list)

    @classmethod
    def miss(cls) -> 'CombatResult':
        """ミス時の結果を生成"""
        return cls(is_hit=False)

@dataclass
class AttackQuality:
    """攻撃の性質（クリティカル・防御）"""
    is_critical: bool
    is_defense: bool
