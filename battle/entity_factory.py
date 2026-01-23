"""エンティティ生成ファクトリ"""

import random
from core.ecs import World
from components.common import NameComponent, PositionComponent
from components.battle import (GaugeComponent, TeamComponent, RenderComponent,
                               BattleContextComponent, PartComponent, HealthComponent,
                               AttackComponent, PartListComponent, MedalComponent, DefeatedComponent,
                               MobilityComponent)
from components.battle_flow import BattleFlowComponent
from components.input import InputComponent
from data.parts_data_manager import get_parts_manager
from data.save_data_manager import get_save_manager
from battle.constants import TEAM_SETTINGS, PartType, TeamType, GaugeStatus
from battle.attributes import AttributeLogic

class BattleEntityFactory:
    """バトルに必要なエンティティを生成するファクトリ"""

    @staticmethod
    def create_medabot_from_setup(world: World, setup: dict) -> dict:
        pm = get_parts_manager()
        parts = {}
        
        # メダルの属性を取得
        medal_attr = "undefined"
        if "medal" in setup:
            medal_data = pm.get_medal_data(setup["medal"])
            medal_attr = medal_data.get("attribute", "undefined")

        for p_type, p_id in setup["parts"].items():
            data = pm.get_part_data(p_id)
            
            # ステータスとボーナスの計算
            stats = BattleEntityFactory._calculate_stats_with_bonus(data, p_type, medal_attr)

            parts[p_type] = BattleEntityFactory._create_part_entity(
                world, 
                p_type, 
                data.get("name", p_id), 
                stats
            )
        return parts

    @staticmethod
    def _calculate_stats_with_bonus(data: dict, part_type: str, medal_attr: str) -> dict:
        """パーツデータとメダル属性に基づいて、ボーナス適用後のステータスを計算する"""
        stats = {
            "hp": data.get("hp", 0),
            "attack": data.get("attack"), # None許容
            "base_attack": data.get("attack"),
            "success": data.get("success", 0),
            "mobility": data.get("mobility", 0),
            "defense": data.get("defense", 0),
            "trait": data.get("trait"),
            "attribute": data.get("attribute", "undefined"),
            "time_modifier": 1.0 # 充填・冷却時間補正 (デフォルト1.0)
        }
        
        # 属性ボーナス計算ロジックを外部モジュールに委譲
        AttributeLogic.apply_passive_stats_bonus(stats, part_type, medal_attr)
                    
        return stats

    @staticmethod
    def _create_part_entity(world: World, part_type: str, name: str, stats: dict) -> int:
        """内部用パーツ生成ヘルパー"""
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
                stats["time_modifier"]
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
    def create_teams(world: World, player_count: int, enemy_count: int, px: int, ex: int, yoff: int, spacing: int, gw: int, gh: int):
        save_mgr = get_save_manager()
        pm = get_parts_manager()

        # プレイヤーチーム生成
        for i in range(player_count):
            setup = save_mgr.get_machine_setup(i)
            BattleEntityFactory._create_team_unit(
                world, i, setup, TeamType.PLAYER, px, yoff, spacing, gw, gh, pm
            )

        # エネミーチーム生成 (ランダム構成)
        medal_ids = pm.get_part_ids_for_type("medal")
        head_ids = pm.get_part_ids_for_type("head")
        r_arm_ids = pm.get_part_ids_for_type("right_arm")
        l_arm_ids = pm.get_part_ids_for_type("left_arm")
        legs_ids = pm.get_part_ids_for_type("legs")

        for i in range(enemy_count):
            # メダルとパーツをランダムに取得
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
                world, i, setup, TeamType.ENEMY, ex, yoff, spacing, gw, gh, pm
            )

    @staticmethod
    def _create_team_unit(world, index, setup, team_type, base_x, y_off, spacing, gw, gh, pm):
        """チームの1機体を生成するヘルパーメソッド"""
        # パーツ群（実体）の生成
        parts = BattleEntityFactory.create_medabot_from_setup(world, setup)
        
        # メダロット（本体）の生成
        eid = world.create_entity()
        
        medal_data = pm.get_medal_data(setup["medal"])
        world.add_component(eid, MedalComponent(
            setup["medal"], 
            medal_data["name"], 
            medal_data["nickname"],
            medal_data.get("personality", "random"),
            medal_data.get("attribute", "undefined")
        ))
        
        world.add_component(eid, PositionComponent(base_x, y_off + index * spacing))
        
        # チーム設定の適用
        settings = TEAM_SETTINGS.get(team_type, TEAM_SETTINGS[TeamType.ENEMY])
        world.add_component(eid, GaugeComponent(1.0, settings['gauge_speed'], GaugeStatus.ACTION_CHOICE))
        
        # リーダー判定
        is_leader = (index == 0)
        world.add_component(eid, TeamComponent(team_type, settings['color'], is_leader=is_leader))
        
        world.add_component(eid, RenderComponent(30, 15, gw, gh))
        world.add_component(eid, DefeatedComponent())
        
        # パーツリストの紐付け
        plist = PartListComponent()
        plist.parts = parts
        world.add_component(eid, plist)