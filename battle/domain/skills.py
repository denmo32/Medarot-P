"""行動（Skill）に関連するロジック（Strategyパターン）"""

from abc import ABC, abstractmethod
from typing import Tuple
from battle.constants import SkillType, GaugeStatus

class SkillBehavior(ABC):
    """スキルの振る舞いを定義する基底クラス"""

    @property
    @abstractmethod
    def name(self) -> str:
        """日本語でのスキル名"""
        pass

    def get_time_modifier(self) -> float:
        """充填・冷却時間の補正係数を返す（デフォルト1.0）"""
        return 1.0

    def get_offensive_bonuses(self, my_mobility: int, my_defense: int) -> Tuple[int, int]:
        """
        攻撃時のボーナス計算を行う。
        Returns: (success_bonus, attack_bonus)
        """
        return 0, 0

    def get_defensive_penalty(self, gauge_status: str) -> Tuple[bool, bool, bool]:
        """
        このスキルを使用中の機体が攻撃を受けた際のペナルティを判定する。
        Returns: (prevent_defense, force_hit, force_critical)
        - prevent_defense: 防御不能（回避は可能）
        - force_hit: 回避不能（命中確定）
        - force_critical: クリティカル確定
        """
        return False, False, False


class ShootSkill(SkillBehavior):
    """撃つ：充填・冷却時間が短縮される"""
    @property
    def name(self) -> str:
        return "撃つ"

    def get_time_modifier(self) -> float:
        return 0.8

class StrikeSkill(SkillBehavior):
    """殴る：機動に応じて成功アップ。チャージ中は防御不可。"""
    @property
    def name(self) -> str:
        return "殴る"

    def get_offensive_bonuses(self, my_mobility: int, my_defense: int) -> Tuple[int, int]:
        # 機動の25%を成功に加算
        return int(my_mobility * 0.25), 0

    def get_defensive_penalty(self, gauge_status: str) -> Tuple[bool, bool, bool]:
        # チャージ中は防御不可
        if gauge_status == GaugeStatus.CHARGING:
            return True, False, False
        return False, False, False

class AimedShotSkill(SkillBehavior):
    """狙い撃ち：耐久(防御)に応じて成功アップ。チャージ中は回避不可。"""
    @property
    def name(self) -> str:
        return "狙い撃ち"

    def get_offensive_bonuses(self, my_mobility: int, my_defense: int) -> Tuple[int, int]:
        # 耐久の50%を成功に加算
        return int(my_defense * 0.50), 0

    def get_defensive_penalty(self, gauge_status: str) -> Tuple[bool, bool, bool]:
        # チャージ中は回避不可（命中確定）
        if gauge_status == GaugeStatus.CHARGING:
            return False, True, False
        return False, False, False

class RecklessSkill(SkillBehavior):
    """我武者羅：機動と耐久に応じて威力アップ。チャージ・冷却中は防御回避不可かつ被クリティカル。"""
    @property
    def name(self) -> str:
        return "我武者羅"

    def get_offensive_bonuses(self, my_mobility: int, my_defense: int) -> Tuple[int, int]:
        # 機動の25% + 耐久の25% を威力に加算
        return 0, int(my_mobility * 0.25) + int(my_defense * 0.25)

    def get_defensive_penalty(self, gauge_status: str) -> Tuple[bool, bool, bool]:
        # チャージ中および冷却中は絶対ヒット、防御不可、クリティカル確定
        if gauge_status in [GaugeStatus.CHARGING, GaugeStatus.COOLDOWN]:
            return True, True, True
        return False, False, False


class SkillRegistry:
    """SkillBehaviorのカタログ（Registry）"""
    
    _behaviors = {
        SkillType.SHOOT: ShootSkill(),
        SkillType.STRIKE: StrikeSkill(),
        SkillType.AIMED_SHOT: AimedShotSkill(),
        SkillType.RECKLESS: RecklessSkill(),
    }
    
    # デフォルトは「撃つ」にしておく（安全策）
    _default = ShootSkill()

    @classmethod
    def get(cls, skill_type: str) -> SkillBehavior:
        """IDに応じたスキル振る舞いを返す"""
        return cls._behaviors.get(skill_type, cls._default)