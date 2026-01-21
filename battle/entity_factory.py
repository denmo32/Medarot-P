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
from battle.constants import TEAM_SETTINGS, PartType, TeamType, GaugeStatus

class BattleEntityFactory:
    """バトルに必要なエンティティを生成するファクトリ"""

    @staticmethod
    def create_part(world: World, part_type: str, name: str, hp: int, trait: str = None, 
                    attack: int = None, success: int = 0, mobility: int = 0, defense: int = 0, attribute: str = "undefined") -> int:
        eid = world.create_entity()
        world.add_component(eid, NameComponent(name))
        world.add_component(eid, PartComponent(part_type, attribute))
        world.add_component(eid, HealthComponent(hp, hp))
        
        if attack is not None:
            world.add_component(eid, AttackComponent(attack, trait, success))
        
        if part_type == PartType.LEGS:
            world.add_component(eid, MobilityComponent(mobility, defense))
            
        return eid

    @staticmethod
    def create_medabot_from_setup(world: World, setup: dict) -> dict:
        pm = get_parts_manager()
        parts = {}
        
        # メダルの属性を取得（脚部ボーナス計算用）
        medal_attr = "undefined"
        if "medal" in setup:
            medal_data = pm.get_medal_data(setup["medal"])
            medal_attr = medal_data.get("attribute", "undefined")

        for p_type, p_id in setup["parts"].items():
            data = pm.get_part_data(p_id)
            
            # 属性取得
            part_attr = data.get("attribute", "undefined")
            
            # 脚部ボーナス計算：メダルと脚部の属性が一致した場合、機動+5
            mobility = data.get("mobility", 0)
            if p_type == PartType.LEGS and medal_attr != "undefined" and medal_attr == part_attr:
                mobility += 5
            
            parts[p_type] = BattleEntityFactory.create_part(
                world, 
                p_type, 
                data.get("name", p_id), 
                data.get("hp", 0), 
                data.get("trait"), 
                data.get("attack"),
                data.get("success", 0),
                mobility,
                data.get("defense", 0),
                part_attr
            )
        return parts

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

        # エネミーチーム生成
        for i in range(enemy_count):
            # メダルとパーツをランダム風に取得（現在は固定パターンのため簡易実装）
            # インデックスに基づいて異なる機体構成を割り当てる
            medal_idx = (i + 3) % 10
            parts_offset = i % 3
            
            medal_id = pm.get_part_ids_for_type("medal")[medal_idx]
            setup = {
                "parts": {
                    t: pm.get_part_ids_for_type(t)[2 - parts_offset] 
                    for t in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]
                },
                "medal": medal_id
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