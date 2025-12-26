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
    """バトルに必要なエンティティを生成するファクトリ"""

    @staticmethod
    def create_part(world: World, part_type: str, name: str, hp: int, trait: str = None, attack: int = None) -> int:
        eid = world.create_entity()
        world.add_component(eid, NameComponent(name))
        world.add_component(eid, PartComponent(part_type))
        world.add_component(eid, HealthComponent(hp, hp))
        if attack is not None:
            world.add_component(eid, AttackComponent(attack, trait))
        return eid

    @staticmethod
    def create_medabot_from_setup(world: World, setup: dict) -> dict:
        pm = get_parts_manager()
        parts = {}
        for p_type, p_id in setup["parts"].items():
            data = pm.get_part_data(p_id)
            parts[p_type] = BattleEntityFactory.create_part(world, p_type, data.get("name", p_id), 
                                                            data.get("hp", 0), data.get("trait"), data.get("attack"))
        return parts

    @staticmethod
    def create_battle_context(world: World) -> int:
        eid = world.create_entity()
        world.add_component(eid, BattleContextComponent())
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

        for i in range(player_count):
            setup = save_mgr.get_machine_setup(i)
            parts = BattleEntityFactory.create_medabot_from_setup(world, setup)
            eid = world.create_entity()
            medal_data = pm.get_medal_data(setup["medal"])
            world.add_component(eid, MedalComponent(setup["medal"], medal_data["name"], medal_data["nickname"]))
            world.add_component(eid, PositionComponent(px, yoff + i * spacing))
            world.add_component(eid, GaugeComponent(1.0, 0.3, GaugeComponent.ACTION_CHOICE))
            world.add_component(eid, TeamComponent("player", (0, 100, 200)))
            world.add_component(eid, RenderComponent(30, 15, gw, gh))
            world.add_component(eid, DefeatedComponent())
            plist = PartListComponent()
            plist.parts = parts
            world.add_component(eid, plist)

        for i in range(enemy_count):
            medal_id = pm.get_part_ids_for_type("medal")[(i + 3) % 10]
            setup = {"parts": {t: pm.get_part_ids_for_type(t)[2 - (i % 3)] for t in ["head", "right_arm", "left_arm", "legs"]}, "medal": medal_id}
            parts = BattleEntityFactory.create_medabot_from_setup(world, setup)
            eid = world.create_entity()
            medal_data = pm.get_medal_data(medal_id)
            world.add_component(eid, MedalComponent(medal_id, medal_data["name"], medal_data["nickname"]))
            world.add_component(eid, PositionComponent(ex, yoff + i * spacing))
            world.add_component(eid, GaugeComponent(1.0, 0.25, GaugeComponent.ACTION_CHOICE))
            world.add_component(eid, TeamComponent("enemy", (200, 0, 0)))
            world.add_component(eid, RenderComponent(30, 15, gw, gh))
            world.add_component(eid, DefeatedComponent())
            plist = PartListComponent()
            plist.parts = parts
            world.add_component(eid, plist)