"""エンティティ生成ファクトリ"""

import json
from core.ecs import World
from components.common import NameComponent, PositionComponent
from components.battle import (GaugeComponent, TeamComponent, RenderComponent,
                               BattleContextComponent, PartComponent, HealthComponent, 
                               AttackComponent, PartListComponent, DefeatedComponent)
from components.input import InputComponent

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
    def create_medabot_parts(world: World, is_player: bool = True) -> dict:
        """Medabotのパーツ一式を生成（JSONデータから）"""
        with open('data/parts_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        parts_key = "player_parts" if is_player else "enemy_parts"
        parts_data = data[parts_key]

        parts = {}
        for part_type, part_info in parts_data.items():
            name = part_info["name"]
            hp = part_info["hp"]
            attack = part_info.get("attack")  # 脚部にはattackがない
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

        # プレイヤー生成
        for i in range(player_count):
            # パーツエンティティの作成
            parts = BattleEntityFactory.create_medabot_parts(world, is_player=True)

            # Medabotエンティティの作成
            e = world.create_entity()
            world.add_component(e.id, NameComponent(f"ロボ{i+1}"))
            world.add_component(e.id, PositionComponent(px, yoff + i * spacing))
            world.add_component(e.id, GaugeComponent(1.0, 0.3, GaugeComponent.ACTION_CHOICE))
            world.add_component(e.id, TeamComponent("player", (0, 100, 200)))
            world.add_component(e.id, RenderComponent(30, 15, gw, gh))
            world.add_component(e.id, DefeatedComponent())

            # パーツリストの追加
            part_list = PartListComponent()
            part_list.parts = parts
            world.add_component(e.id, part_list)

        # エネミー生成
        for i in range(enemy_count):
            # パーツエンティティの作成
            parts = BattleEntityFactory.create_medabot_parts(world, is_player=False)

            # Medabotエンティティの作成
            e = world.create_entity()
            world.add_component(e.id, NameComponent(f"敵ロボ{i+1}"))
            world.add_component(e.id, PositionComponent(ex, yoff + i * spacing))
            world.add_component(e.id, GaugeComponent(1.0, 0.25, GaugeComponent.ACTION_CHOICE))
            world.add_component(e.id, TeamComponent("enemy", (200, 0, 0)))
            world.add_component(e.id, RenderComponent(30, 15, gw, gh))
            world.add_component(e.id, DefeatedComponent())

            # パーツリストの追加
            part_list = PartListComponent()
            part_list.parts = parts
            world.add_component(e.id, part_list)