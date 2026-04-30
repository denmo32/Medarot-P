"""行動スキル（Skill）の振る舞いロジック"""

from abc import ABC, abstractmethod
from typing import Tuple
from domain.constants import SkillType, GaugeStatus

class SkillBehavior(ABC):
    """スキルの振る舞いを定義する基底クラス"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    def get_time_modifier(self) -> float:
        return 1.0

    def get_offensive_bonuses(self, my_mobility: int, my_defense: int) -> Tuple[int, int]:
        return 0, 0

    def get_defensive_penalty(self, gauge_status: str) -> Tuple[bool, bool, bool]:
        """
        Returns: (prevent_defense, force_hit, force_critical)
        """
        return False, False, False


class ShootSkill(SkillBehavior):
    @property
    def name(self) -> str: return "撃つ"
    def get_time_modifier(self) -> float: return 0.8

class StrikeSkill(SkillBehavior):
    @property
    def name(self) -> str: return "殴る"
    def get_offensive_bonuses(self, my_mobility: int, my_defense: int) -> Tuple[int, int]:
        return int(my_mobility * 0.25), 0
    def get_defensive_penalty(self, gauge_status: str) -> Tuple[bool, bool, bool]:
        if gauge_status == GaugeStatus.CHARGING: return True, False, False
        return False, False, False

class AimedShotSkill(SkillBehavior):
    @property
    def name(self) -> str: return "狙い撃ち"
    def get_offensive_bonuses(self, my_mobility: int, my_defense: int) -> Tuple[int, int]:
        return int(my_defense * 0.50), 0
    def get_defensive_penalty(self, gauge_status: str) -> Tuple[bool, bool, bool]:
        if gauge_status == GaugeStatus.CHARGING: return False, True, False
        return False, False, False

class RecklessSkill(SkillBehavior):
    @property
    def name(self) -> str: return "我武者羅"
    def get_offensive_bonuses(self, my_mobility: int, my_defense: int) -> Tuple[int, int]:
        return 0, int(my_mobility * 0.25) + int(my_defense * 0.25)
    def get_defensive_penalty(self, gauge_status: str) -> Tuple[bool, bool, bool]:
        if gauge_status in [GaugeStatus.CHARGING, GaugeStatus.COOLDOWN]:
            return True, True, True
        return False, False, False


class SkillRegistry:
    _behaviors = {
        SkillType.SHOOT: ShootSkill(),
        SkillType.STRIKE: StrikeSkill(),
        SkillType.AIMED_SHOT: AimedShotSkill(),
        SkillType.RECKLESS: RecklessSkill(),
    }
    _default = ShootSkill()

    @classmethod
    def get(cls, skill_type: str) -> SkillBehavior:
        return cls._behaviors.get(skill_type, cls._default)