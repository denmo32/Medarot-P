"""エンティティ生成ファクトリ"""

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

class BattleEntityFactory:
    """バトルに必要なエンティティを生成するファクトリ"""

    @staticmethod
    def create_part(world: World, part_type: str, name: str, hp: int, trait: str = None, 
                    attack: int = None, success: int = 0, mobility: int = 0, defense: int = 0) -> int:
        eid = world.create_entity()
        world.add_component(eid, NameComponent(name))
        world.add_component(eid, PartComponent(part_type))
        world.add_component(eid, HealthComponent(hp, hp))
        
        if attack is not None:
            world.add_component(eid, AttackComponent(attack, trait, success))
        
        if part_type == "legs":
            world.add_component(eid, MobilityComponent(mobility, defense))
            
        return eid

    @staticmethod
    def create_medabot_from_setup(world: World, setup: dict) -> dict:
        pm = get_parts_manager()
        parts = {}
        for p_type, p_id in setup["parts"].items():
            data = pm.get_part_data(p_id)
            parts[p_type] = BattleEntityFactory.create_part(
                world, 
                p_type, 
                data.get("name", p_id), 
                data.get("hp", 0), 
                data.get("trait"), 
                data.get("attack"),
                data.get("success", 0),
                data.get("mobility", 0),
                data.get("defense", 0)
            )
        return parts

    @staticmethod
    def create_battle_context(world: World) -> int:
        eid = world.create_entity()
        world.add_component(eid, BattleContextComponent())
        world.add_component(eid, BattleFlowComponent()) # Flowコンポーネントを追加
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
                world, i, setup, "player", px, yoff, spacing, gw, gh, pm
            )

        # エネミーチーム生成
        for i in range(enemy_count):
            # 適当な構成を生成
            medal_id = pm.get_part_ids_for_type("medal")[(i + 3) % 10]
            setup = {
                "parts": {t: pm.get_part_ids_for_type(t)[2 - (i % 3)] for t in ["head", "right_arm", "left_arm", "legs"]},
                "medal": medal_id
            }
            BattleEntityFactory._create_team_unit(
                world, i, setup, "enemy", ex, yoff, spacing, gw, gh, pm
            )

    @staticmethod
    def _create_team_unit(world, index, setup, team_type, base_x, y_off, spacing, gw, gh, pm):
        """チームの1機体を生成するヘルパーメソッド"""
        parts = BattleEntityFactory.create_medabot_from_setup(world, setup)
        eid = world.create_entity()
        
        medal_data = pm.get_medal_data(setup["medal"])
        
        world.add_component(eid, MedalComponent(
            setup["medal"], 
            medal_data["name"], 
            medal_data["nickname"],
            medal_data.get("personality", "random")
        ))
        
        world.add_component(eid, PositionComponent(base_x, y_off + index * spacing))
        
        # チームごとのパラメータ設定
        if team_type == "player":
            gauge_speed = 0.3
            color = (0, 100, 200)
        else:
            gauge_speed = 0.25
            color = (200, 0, 0)

        world.add_component(eid, GaugeComponent(1.0, gauge_speed, GaugeComponent.ACTION_CHOICE))
        
        # 1機目をリーダーに設定
        is_leader = (index == 0)
        world.add_component(eid, TeamComponent(team_type, color, is_leader=is_leader))
        
        world.add_component(eid, RenderComponent(30, 15, gw, gh))
        world.add_component(eid, DefeatedComponent())
        
        plist = PartListComponent()
        plist.parts = parts
        world.add_component(eid, plist)