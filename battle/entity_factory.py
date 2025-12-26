"""エンティティ生成ファクトリ"""

from core.ecs import World
from components.common import NameComponent, PositionComponent
from components.battle import (GaugeComponent, TeamComponent, RenderComponent,
                               BattleContextComponent, PartComponent, HealthComponent,
                               AttackComponent, PartListComponent, MedalComponent, DefeatedComponent)
from components.input import InputComponent
from data.parts_data_manager import get_parts_manager
from data.save_data_manager import get_save_manager

class BattleEntityFactory:
    """バトルに必要なエンティティを生成するファクトリクラス"""

    @staticmethod
    def create_part(world: World, part_type: str, name: str, hp: int, attack: int = None) -> int:
        """個別のパーツエンティティを生成"""
        entity = world.create_entity()
        world.add_component(entity.id, NameComponent(name))
        world.add_component(entity.id, PartComponent(part_type))
        world.add_component(entity.id, HealthComponent(hp, hp))
        if attack is not None:  # 脚部以外
            world.add_component(entity.id, AttackComponent(attack))
        return entity.id

    @staticmethod
    def create_medabot_from_setup(world: World, setup: dict) -> dict:
        """セットアップデータからMedabotのパーツ一式を生成"""
        pm = get_parts_manager()
        parts = {}
        
        for part_type, part_id in setup["parts"].items():
            part_data = pm.get_part_data(part_id)
            name = part_data.get("name", part_id)
            hp = part_data.get("hp", 0)
            attack = part_data.get("attack")
            parts[part_type] = BattleEntityFactory.create_part(world, part_type, name, hp, attack)
            
        return parts

    @staticmethod
    def create_battle_context(world: World) -> int:
        """バトルコンテキストエンティティを生成"""
        entity = world.create_entity()
        world.add_component(entity.id, BattleContextComponent())
        return entity.id

    @staticmethod
    def create_input_manager(world: World) -> int:
        """入力管理エンティティを生成"""
        entity = world.create_entity()
        world.add_component(entity.id, InputComponent())
        return entity.id

    @staticmethod
    def create_teams(world: World, player_count: int, enemy_count: int,
                     px: int, ex: int, yoff: int, spacing: int,
                     gw: int, gh: int):
        """プレイヤーとエネミーのチームを生成"""
        save_mgr = get_save_manager()
        pm = get_parts_manager()

        # プレイヤー生成（SaveDataManagerのデータを使用）
        for i in range(player_count):
            setup = save_mgr.get_machine_setup(i)
            parts = BattleEntityFactory.create_medabot_from_setup(world, setup)

            e = world.create_entity()
            world.add_component(e.id, NameComponent(setup["name"]))
            
            # メダルコンポーネント付与
            medal_data = pm.get_medal_data(setup["medal"])
            world.add_component(e.id, MedalComponent(setup["medal"], medal_data["name"], medal_data["nickname"]))
            
            world.add_component(e.id, PositionComponent(px, yoff + i * spacing))
            world.add_component(e.id, GaugeComponent(1.0, 0.3, GaugeComponent.ACTION_CHOICE))
            world.add_component(e.id, TeamComponent("player", (0, 100, 200)))
            world.add_component(e.id, RenderComponent(30, 15, gw, gh))
            world.add_component(e.id, DefeatedComponent())

            part_list = PartListComponent()
            part_list.parts = parts
            world.add_component(e.id, part_list)

        # エネミー生成（適当なメダルを割り当て）
        for i in range(enemy_count):
            medal_id = pm.get_part_ids_for_type("medal")[(i + 3) % 10]
            enemy_setup = {
                "parts": {
                    "head": pm.get_part_ids_for_type("head")[2 - (i % 3)],
                    "right_arm": pm.get_part_ids_for_type("right_arm")[2 - (i % 3)],
                    "left_arm": pm.get_part_ids_for_type("left_arm")[2 - (i % 3)],
                    "legs": pm.get_part_ids_for_type("legs")[2 - (i % 3)],
                },
                "medal": medal_id
            }
            parts = BattleEntityFactory.create_medabot_from_setup(world, enemy_setup)

            e = world.create_entity()
            world.add_component(e.id, NameComponent(f"敵ロボ{i+1}"))
            
            medal_data = pm.get_medal_data(medal_id)
            world.add_component(e.id, MedalComponent(medal_id, medal_data["name"], medal_data["nickname"]))

            world.add_component(e.id, PositionComponent(ex, yoff + i * spacing))
            world.add_component(e.id, GaugeComponent(1.0, 0.25, GaugeComponent.ACTION_CHOICE))
            world.add_component(e.id, TeamComponent("enemy", (200, 0, 0)))
            world.add_component(e.id, RenderComponent(30, 15, gw, gh))
            world.add_component(e.id, DefeatedComponent())

            part_list = PartListComponent()
            part_list.parts = parts
            world.add_component(e.id, part_list)