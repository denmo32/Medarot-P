# domain/constants.py
"""ゲーム全体で共通の定数・データ型定義"""
from enum import Enum
from typing import Optional, Type, TypeVar

_KT = TypeVar("_KT", bound="KeyedEnum")


class KeyedEnum(str, Enum):
    """キー正規化（`from_key`）を共通化した Enum の基底クラス。"""

    @classmethod
    def _fallback(cls: Type[_KT]) -> Optional[_KT]:
        return None

    @classmethod
    def _match_by_name(cls) -> bool:
        return False

    @classmethod
    def from_key(cls: Type[_KT], key: object) -> Optional[_KT]:
        if isinstance(key, cls):
            return key
        if not isinstance(key, str) or not key:
            return cls._fallback()
        try:
            return cls(key)
        except ValueError:
            pass
        if cls._match_by_name():
            upper = key.upper()
            for member in cls:
                if member.name == upper:
                    return member
        return cls._fallback()


class _RandomFallbackEnum(KeyedEnum):
    """日本語の値と英語識別子名で解決し、未知のキーは RANDOM にフォールバックする Enum の基底"""

    @property
    def display_name(self) -> str:
        return self.value

    @classmethod
    def _fallback(cls: Type[_KT]) -> Optional[_KT]:
        return cls.RANDOM

    @classmethod
    def _match_by_name(cls) -> bool:
        return True


class CustomizeState(KeyedEnum):
    """カスタマイズ画面の操作ステート"""
    ROBOT_SELECT = "robot_select"
    SLOT_SELECT = "slot_select"
    PART_LIST_SELECT = "part_list_select"


# コマンドメニューのスロットインデックス（features の入力規則と ui のレイアウトが共有する契約）
COMMAND_MENU_HEAD_INDEX = 0
COMMAND_MENU_RIGHT_ARM_INDEX = 1
COMMAND_MENU_LEFT_ARM_INDEX = 2
COMMAND_MENU_SKIP_INDEX = 3


class AccentState(str, Enum):
    """機体およびパーツの視覚的状態アクセント"""
    CHARGING = "charging"
    COOLDOWN = "cooldown"
    READY = "ready"
    STOPPED = "stopped"
    NEUTRAL = "neutral"


class BadgeKind(str, Enum):
    """状態バッジの種別"""
    STOP = "stop"
    BLOCK = "block"
    PROTECT = "protect"
    SUCCESS_UP = "success_up"


class TeamType(str, Enum):
    PLAYER = "player"
    ENEMY = "enemy"


class PartType(KeyedEnum):
    """部位（パーツの装着箇所）"""
    HEAD = "head"
    RIGHT_ARM = "right_arm"
    LEFT_ARM = "left_arm"
    LEGS = "legs"

    @property
    def label(self) -> str:
        return _PART_LABELS.get(self, self.value)


class CustomizeSlot(KeyedEnum):
    """カスタマイズ画面のスロット識別子"""
    MEDAL = "medal"
    HEAD = "head"
    RIGHT_ARM = "right_arm"
    LEFT_ARM = "left_arm"
    LEGS = "legs"

    @property
    def is_medal(self) -> bool:
        return self is CustomizeSlot.MEDAL

    @property
    def part_type(self) -> Optional[PartType]:
        return PartType.from_key(self.value) if not self.is_medal else None

    @property
    def label(self) -> str:
        if self.is_medal:
            return "メダル"
        pt = self.part_type
        return pt.label if pt else self.value


_PART_LABELS = {
    PartType.HEAD: "頭部",
    PartType.RIGHT_ARM: "右腕",
    PartType.LEFT_ARM: "左腕",
    PartType.LEGS: "脚部",
}

# 互換性維持のためのエイリアス
PART_TYPE_LABELS = {
    CustomizeSlot.MEDAL: "メダル",
    PartType.HEAD: "頭部",
    PartType.RIGHT_ARM: "右腕",
    PartType.LEFT_ARM: "左腕",
    PartType.LEGS: "脚部",
}

CUSTOMIZE_SLOTS = (
    CustomizeSlot.MEDAL,
    CustomizeSlot.HEAD,
    CustomizeSlot.RIGHT_ARM,
    CustomizeSlot.LEFT_ARM,
    CustomizeSlot.LEGS,
)

ACTIONABLE_PART_TYPES = (PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM)
ALL_PART_TYPES = (
    PartType.HEAD,
    PartType.RIGHT_ARM,
    PartType.LEFT_ARM,
    PartType.LEGS,
)


class AttributeType(KeyedEnum):
    """属性種別"""
    SPEED = "speed"
    POWER = "power"
    TECHNIQUE = "technique"
    UNDEFINED = "undefined"

    @property
    def display_name(self) -> str:
        return _ATTRIBUTE_DISPLAY_NAMES.get(self, self.value)

    @classmethod
    def _fallback(cls: Type[_KT]) -> Optional[_KT]:
        return cls.UNDEFINED


_ATTRIBUTE_DISPLAY_NAMES = {
    AttributeType.SPEED: "スピード",
    AttributeType.POWER: "パワー",
    AttributeType.TECHNIQUE: "テクニック",
    AttributeType.UNDEFINED: "-",
}


class PersonalityType(_RandomFallbackEnum):
    """メダルの性格"""
    RANDOM = "ランダム"
    CHASER = "チェイサー"
    CHALLENGER = "チャレンジャー"
    SWEEPER = "スイーパー"
    STOPPER = "ストッパー"


class TacticsType(_RandomFallbackEnum):
    """コマンダーの戦術"""
    RANDOM = "ランダム"


class SkillType(KeyedEnum):
    RIFLE = "ライフル"
    GATLING = "ガトリング"
    MISSILE = "ミサイル"
    SWORD = "ソード"
    HAMMER = "ハンマー"
    THUNDER = "サンダー"
    STUN = "スタン"
    SCAN = "スキャン"
    BLOCK = "ブロック"
    PROTECT = "プロテクト"
    COOL_PLANT = "クールプラント"
    SHOOTING_TRAP = "射撃トラップ"
    REPAIR = "リペア"
    RESTORE = "レストア"


class ActionCategory(str, Enum):
    SHOOTING = "shooting"
    MELEE = "melee"
    CONTROL = "control"
    SETUP = "setup"
    DEFENSE = "defense"
    CARE = "care"


class SkillKind(str, Enum):
    ATTACK = "attack"
    EFFECT = "effect"


class SkillPresentation(str, Enum):
    CUTIN = "cutin"
    LOG_ONLY = "log_only"
    NONE = "none"


class TargetTiming(str, Enum):
    ON_CHARGE = "on_charge"
    ON_EXECUTE = "on_execute"
    NONE = "none"


class HitPolicy(str, Enum):
    STANDARD = "standard"
    NEVER_MISS = "never_miss"
    AUTO_HIT = "auto_hit"


class TargetRule(str, Enum):
    ENEMY_BY_PERSONALITY = "enemy_by_personality"
    CLOSEST_ENEMY = "closest_enemy"
    ENEMY_RANDOM = "enemy_random"
    FRIEND_LEAST_HP = "friend_least_hp"
    FRIEND_ANY_BROKEN = "friend_any_broken"
    SELF = "self"


class ActionType(KeyedEnum):
    @classmethod
    def _match_by_name(cls) -> bool:
        return True

    def __new__(cls, value: str, category: ActionCategory):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.category = category
        return obj

    SHOOT = ("撃つ", ActionCategory.SHOOTING)
    AIMED_SHOT = ("狙い撃ち", ActionCategory.SHOOTING)
    STRIKE = ("殴る", ActionCategory.MELEE)
    RECKLESS = ("我武者羅", ActionCategory.MELEE)
    SUPPORT = ("支援", ActionCategory.CONTROL)
    DISRUPT = ("妨害", ActionCategory.CONTROL)
    PLANT = ("供給", ActionCategory.SETUP)
    TRAP = ("掛罠", ActionCategory.SETUP)
    COVER = ("護衛", ActionCategory.DEFENSE)
    SELF_DEFENSE = ("自衛", ActionCategory.DEFENSE)
    HEAL = ("修復", ActionCategory.CARE)
    RECOVER = ("復元", ActionCategory.CARE)


class GaugeStatus(str, Enum):
    CHARGING = "charging"
    EXECUTING = "executing"
    COOLDOWN = "cooldown"
    READY = "ready"


class EffectType(str, Enum):
    STOP = "stop"
    SUCCESS_UP = "success_up"
    BLOCK = "block"
    PROTECT = "protect"

    @property
    def is_stance(self) -> bool:
        return self in (EffectType.BLOCK, EffectType.PROTECT)


class EffectStackPolicy(str, Enum):
    REFRESH_MAX = "refresh_max"
    OVERWRITE = "overwrite"
    STACK = "stack"
    CHARGES_MAX = "charges_max"