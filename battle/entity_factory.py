"""エンティティ生成ファクトリ"""

import json
from core.ecs import World
from components.common import NameComponent, PositionComponent
from components.battle import (GaugeComponent, TeamComponent, RenderComponent,
                               BattleContextComponent, PartComponent, HealthComponent,
                               AttackComponent, PartListComponent, DefeatedComponent)
from components.input import InputComponent
from data.parts_data_manager import get_parts_manager

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
    def create_medabot_parts(world: World) -> dict:
        """Medabotのパーツ一式を生成（デフォルトパーツを使用）"""
        parts_manager = get_parts_manager()

        parts = {}
        part_types = ['head', 'right_arm', 'left_arm', 'legs']

        for part_type in part_types:
            # 各部位の最初のIDを取得（デフォルトパーツ）
            part_ids = parts_manager.get_part_ids_for_type(part_type)
            if not part_ids:
                continue  # パーツがない場合はスキップ
            default_part_id = part_ids[0]  # 最初のIDを使用

            # パーツデータを取得
            part_data = parts_manager.get_part_data(default_part_id)
            name = part_data.get("name", default_part_id)
            hp = part_data.get("hp", 0)
            attack = part_data.get("attack")  # 脚部にはattackがない場合None

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
            parts = BattleEntityFactory.create_medabot_parts(world)

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
            parts = BattleEntityFactory.create_medabot_parts(world)

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