"""エンティティ生成ファクトリ"""

import random
from typing import Optional
from core.ecs import World
from components.common_component import NameComponent, PositionComponent
from components.battle_component import (GaugeComponent, TeamComponent, RenderComponent,
                               BattleContextComponent, PartComponent, HealthComponent,
                               AttackComponent, PartListComponent, MedalComponent, DefeatedComponent,
                               MobilityComponent)
from components.battle_flow_component import BattleFlowComponent
from components.input_component import InputComponent
from data.game_data_manager import GameDataManager
from data.save_data_manager import SaveDataManager
from domain.models import PartData, MedalData
from ui.config import TEAM_SETTINGS
from battle.constants import PartType, TeamType, GaugeStatus
from battle.mechanics.stats_logic import StatsLogic

class BattleEntityFactory:
    """バトルに必要なエンティティを生成するファクトリ"""

    @staticmethod
    def create_medabot_from_setup(world: World, setup: dict, data_manager: GameDataManager) -> dict:
        parts = {}

        medal_attr = "undefined"
        if "medal" in setup:
            medal_data = data_manager.get_medal_data(setup["medal"])
            if medal_data is not None:
                medal_attr = medal_data.attribute

        for p_type, p_id in setup["parts"].items():
            data = data_manager.get_part_data(p_id)
            if data is None:
                continue
            stats = StatsLogic.calculate_initial_stats(data, p_type, medal_attr)

            parts[p_type] = BattleEntityFactory._create_part_entity(
                world,
                p_type,
                data.name,
                stats
            )
        return parts

    @staticmethod
    def _create_part_entity(world: World, part_type: str, name: str, stats: dict) -> int:
        eid = world.create_entity()
        world.add_component(eid, NameComponent(name))
        world.add_component(eid, PartComponent(part_type, stats["attribute"]))
        world.add_component(eid, HealthComponent(stats["hp"], stats["hp"]))
        
        if stats["attack"] is not None:
            world.add_component(eid, AttackComponent(
                stats["attack"], 
                stats["trait"], 
                stats["success"], 
                stats["base_attack"],
                stats["time_modifier"],
                stats["skill"]
            ))
        
        if part_type == PartType.LEGS:
            world.add_component(eid, MobilityComponent(stats["mobility"], stats["defense"]))
            
        return eid

    @staticmethod
    def create_battle_context(world: World) -> int:
        eid = world.create_entity()
        world.add_component(eid, BattleContextComponent())
        world.add_component(eid, BattleFlowComponent())
        return eid

    @staticmethod
    def create_input_manager(world: World) -> int:
        eid = world.create_entity()
        world.add_component(eid, InputComponent())
        return eid

    @staticmethod
    def create_teams(world: World, player_count: int, enemy_count: int, 
                     px_ratio: float, ex_ratio: float, y_start_ratio: float, spacing_ratio: float,
                     data_manager: GameDataManager, save_manager: SaveDataManager):
        
        # 1. プレイヤーチームの生成
        for i in range(player_count):
            setup = save_manager.get_machine_setup(i)
            BattleEntityFactory._create_team_unit(
                world, i, setup, TeamType.PLAYER, px_ratio, y_start_ratio, spacing_ratio, data_manager
            )

        # 2. エネミーチームの生成
        medal_ids = data_manager.get_part_ids_for_type("medal")
        head_ids = data_manager.get_part_ids_for_type("head")
        r_arm_ids = data_manager.get_part_ids_for_type("right_arm")
        l_arm_ids = data_manager.get_part_ids_for_type("left_arm")
        legs_ids = data_manager.get_part_ids_for_type("legs")

        for i in range(enemy_count):
            setup = {
                "parts": {
                    "head": random.choice(head_ids) if head_ids else "head_001",
                    "right_arm": random.choice(r_arm_ids) if r_arm_ids else "rarm_001",
                    "left_arm": random.choice(l_arm_ids) if l_arm_ids else "larm_001",
                    "legs": random.choice(legs_ids) if legs_ids else "legs_001",
                },
                "medal": random.choice(medal_ids) if medal_ids else "medal_001"
            }
            BattleEntityFactory._create_team_unit(
                world, i, setup, TeamType.ENEMY, ex_ratio, y_start_ratio, spacing_ratio, data_manager
            )

    @staticmethod
    def _create_team_unit(world, index, setup, team_type, base_x_ratio, y_start_ratio, spacing_ratio, data_manager):
        """1体の機体とそれに付随するコンポーネントを生成"""
        # 各部位エンティティの生成
        parts = BattleEntityFactory.create_medabot_from_setup(world, setup, data_manager)
        
        # 本体エンティティの生成
        eid = world.create_entity()
        
        medal_data = data_manager.get_medal_data(setup["medal"])
        if medal_data is None:
            # デフォルト値を設定
            medal_data = MedalData(name="", nickname="", personality="random", attribute="undefined")

        world.add_component(eid, MedalComponent(
            setup["medal"],
            medal_data.name,
            medal_data.nickname,
            medal_data.personality,
            medal_data.attribute
        ))
        
        # 描画・配置情報の追加（相対座標）
        # PositionComponentには 0.0 ~ 1.0 の比率を格納する
        world.add_component(eid, PositionComponent(base_x_ratio, y_start_ratio + index * spacing_ratio))
        
        settings = TEAM_SETTINGS.get(team_type, TEAM_SETTINGS[TeamType.ENEMY])
        world.add_component(eid, TeamComponent(team_type, settings['color'], is_leader=(index == 0)))
        
        # RenderComponentのサイズ情報は具体的なピクセル値を持つ必要がなくなりつつあるが、
        # 互換性のため一旦ダミー値または削除を検討。ここでは一旦デフォルト値を入れるが、Renderer側で比率計算する方針。
        world.add_component(eid, RenderComponent(0, 0, 0, 0))
        
        # バトル状態管理用コンポーネントの追加
        world.add_component(eid, GaugeComponent(status=GaugeStatus.ACTION_CHOICE))
        world.add_component(eid, DefeatedComponent())
        
        # パーツリストを機体エンティティに紐付け
        plist = PartListComponent()
        plist.parts = parts
        world.add_component(eid, plist)