"""エンティティ生成ファクトリ"""

from core.ecs import World
from components.common import NameComponent, PositionComponent
from components.battle import GaugeComponent, TeamComponent, RenderComponent, PartHealthComponent, PartAttackComponent, BattleContextComponent
from components.input import InputComponent

class BattleEntityFactory:
    """バトルに必要なエンティティを生成するファクトリクラス"""

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
            e = world.create_entity()
            world.add_component(e.id, NameComponent(f"ロボ{i+1}"))
            # バランス調整されたパラメータ
            world.add_component(e.id, PartHealthComponent(50, 40, 40, 60, 50, 40, 40, 60))
            world.add_component(e.id, PositionComponent(px, yoff + i * spacing))
            world.add_component(e.id, GaugeComponent(0.0, 0.3, GaugeComponent.COOLDOWN))
            world.add_component(e.id, TeamComponent("player", (0, 100, 200)))
            world.add_component(e.id, PartAttackComponent(10, 15, 12))
            world.add_component(e.id, RenderComponent(30, 15, gw, gh))

        # エネミー生成
        for i in range(enemy_count):
            e = world.create_entity()
            world.add_component(e.id, NameComponent(f"敵ロボ{i+1}"))
            world.add_component(e.id, PartHealthComponent(45, 35, 35, 55, 45, 35, 35, 55))
            world.add_component(e.id, PositionComponent(ex, yoff + i * spacing))
            world.add_component(e.id, GaugeComponent(0.0, 0.25, GaugeComponent.COOLDOWN))
            world.add_component(e.id, TeamComponent("enemy", (200, 0, 0)))
            world.add_component(e.id, PartAttackComponent(8, 12, 10))
            world.add_component(e.id, RenderComponent(30, 15, gw, gh))
