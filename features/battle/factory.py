"""バトル関連のオブジェクト生成を担うファクトリクラス（RobotSetup・RNG対応）。"""

import logging
import random
from typing import Dict, List, Optional
from domain.config import PLAYER_COUNT, ENEMY_COUNT
from domain.constants import ALL_PART_TYPES, CustomizeSlot, TeamType, PartType, AttributeType, PersonalityType
from domain.models import GameDataProtocol, MedalData, RobotSetup, SaveDataProtocol
from .models import Robot, Part
from .debug_enemy import (
    ENABLE_CUSTOM_ENEMY,
    CUSTOM_ENEMY_SETUPS,
    DEBUG_PLAYER_COUNT,
    DEBUG_ENEMY_COUNT,
)

logger = logging.getLogger(__name__)

_FALLBACK_PART_ID = {
    PartType.HEAD: "head_001",
    PartType.RIGHT_ARM: "rarm_001",
    PartType.LEFT_ARM: "larm_001",
    PartType.LEGS: "legs_001",
}


class BattleFactory:
    @staticmethod
    def _fallback_medal_data() -> MedalData:
        return MedalData(name="Unknown", nickname="Unknown", personality=PersonalityType.RANDOM,
                         attribute=AttributeType.UNDEFINED)

    @classmethod
    def _resolve_robot_name(cls, setup_name: str, medal_data: MedalData) -> str:
        if medal_data.nickname and medal_data.nickname != "Unknown":
            return medal_data.nickname
        return setup_name or "Medarot"

    @classmethod
    def create_robot(
        cls, team: TeamType, is_leader: bool, setup: RobotSetup, data_manager: GameDataProtocol
    ) -> Robot:
        medal_data = data_manager.get_medal_data(setup.medal_id) or cls._fallback_medal_data()
        name = cls._resolve_robot_name(setup.name, medal_data)

        parts: Dict[PartType, Part] = {}
        for part_type, p_id in setup.part_ids.items():
            p_data = data_manager.get_part_data(p_id)
            if p_data:
                parts[part_type] = Part(part_type, p_data, medal_data)
            else:
                logger.warning(f"機体 '{name}' のパーツ '{p_id}' ({part_type.value}) が見つかりません。")

        return Robot(team=team, is_leader=is_leader, name=name, medal_data=medal_data, parts=parts)

    @classmethod
    def create_robots(
        cls, player_setups: List[RobotSetup], enemy_setups: List[RobotSetup], data_manager: GameDataProtocol
    ) -> List[Robot]:
        robots: List[Robot] = []
        robots.extend(
            cls.create_robot(TeamType.PLAYER, i == 0, setup, data_manager)
            for i, setup in enumerate(player_setups)
        )
        robots.extend(
            cls.create_robot(TeamType.ENEMY, i == 0, setup, data_manager)
            for i, setup in enumerate(enemy_setups)
        )
        return robots

    @classmethod
    def get_player_setups(cls, save_manager: SaveDataProtocol, count: Optional[int] = None) -> List[RobotSetup]:
        target_count = count or (DEBUG_PLAYER_COUNT if DEBUG_PLAYER_COUNT is not None else PLAYER_COUNT)
        target_count = max(1, min(PLAYER_COUNT, target_count))

        setups = []
        for i in range(target_count):
            setup = save_manager.get_robot_setup(i)
            if setup:
                setups.append(setup)
        return setups

    @classmethod
    def get_enemy_setups(
        cls, data_manager: GameDataProtocol, count: Optional[int] = None, rng: Optional[random.Random] = None
    ) -> List[RobotSetup]:
        target_count = count
        if target_count is None:
            if DEBUG_ENEMY_COUNT is not None:
                target_count = DEBUG_ENEMY_COUNT
            elif ENABLE_CUSTOM_ENEMY and CUSTOM_ENEMY_SETUPS:
                target_count = len(CUSTOM_ENEMY_SETUPS)
            else:
                target_count = ENEMY_COUNT

        target_count = max(1, target_count)

        if ENABLE_CUSTOM_ENEMY and CUSTOM_ENEMY_SETUPS:
            return cls._build_custom_enemy_setups(data_manager, target_count, rng)
        return cls.generate_random_enemy_setups(data_manager, target_count, rng)

    @staticmethod
    def _get_enemy_candidate_resources(data_manager: GameDataProtocol):
        medal_ids = data_manager.get_part_ids_for_type(CustomizeSlot.MEDAL) or ["medal_001"]
        part_ids_by_type = {
            part_type: data_manager.get_part_ids_for_type(part_type) or [_FALLBACK_PART_ID[part_type]]
            for part_type in ALL_PART_TYPES
        }
        return medal_ids, part_ids_by_type

    @classmethod
    def _build_custom_enemy_setups(
        cls, data_manager: GameDataProtocol, count: int = ENEMY_COUNT, rng: Optional[random.Random] = None
    ) -> List[RobotSetup]:
        medal_ids, part_ids_by_type = cls._get_enemy_candidate_resources(data_manager)
        setups = []

        for i, custom in enumerate(CUSTOM_ENEMY_SETUPS[:count]):
            custom_parts = dict(custom.get("parts", {}))
            parts = {
                pt: custom_parts.get(pt.value, part_ids_by_type[pt][0])
                for pt in ALL_PART_TYPES
            }
            medal = custom.get("medal", medal_ids[0])
            name = custom.get("name", f"エネミー{i+1}")
            setups.append(RobotSetup(name=name, medal_id=medal, part_ids=parts))

        if len(setups) < count:
            supplements = cls.generate_random_enemy_setups(data_manager, count - len(setups), rng)
            setups.extend(supplements)

        return setups

    @classmethod
    def generate_random_enemy_setups(
        cls, data_manager: GameDataProtocol, count: int = ENEMY_COUNT, rng: Optional[random.Random] = None
    ) -> List[RobotSetup]:
        _rng = rng or random
        medal_ids, part_ids_by_type = cls._get_enemy_candidate_resources(data_manager)

        return [
            RobotSetup(
                name=f"エネミー{i+1}",
                medal_id=_rng.choice(medal_ids),
                part_ids={pt: _rng.choice(part_ids_by_type[pt]) for pt in ALL_PART_TYPES},
            )
            for i in range(count)
        ]