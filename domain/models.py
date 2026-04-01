"""ドメインモデルのデータクラス定義"""

from dataclasses import dataclass
from typing import Optional


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
