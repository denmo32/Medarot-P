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
            # base_attackは補正前の値を想定してattackと同じ値を初期値として渡すが、
            # 呼び出し元で補正が行われている場合はその限りではない。
            # ここではシンプルに受け取ったattackをそのまま設定し、base_attack用引数を追加する形にするのが望ましいが、
            # create_medabot_from_setup側で計算済みの値を渡す設計にする。
            # ただし、AttackComponent側で base_attack を保持する必要があるため、引数を拡張する。
            pass

        # create_partの引数が多くなりすぎているため、コンポーネント生成を個別に処理する形にリファクタリングしつつ実装
        return eid

    @staticmethod
    def _create_part_entity(world: World, part_type: str, name: str, hp: int, trait: str, 
                            attack: int, base_attack: int, success: int, mobility: int, defense: int, attribute: str) -> int:
        """内部用パーツ生成ヘルパー"""
        eid = world.create_entity()
        world.add_component(eid, NameComponent(name))
        world.add_component(eid, PartComponent(part_type, attribute))
        world.add_component(eid, HealthComponent(hp, hp))
        
        if attack is not None:
            world.add_component(eid, AttackComponent(attack, trait, success, base_attack))
        
        if part_type == PartType.LEGS:
            world.add_component(eid, MobilityComponent(mobility, defense))
            
        return eid

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
            part_attr = data.get("attribute", "undefined")
            
            # 基本パラメータの取得
            hp = data.get("hp", 0)
            attack = data.get("attack") # Noneの場合あり
            success = data.get("success", 0)
            mobility = data.get("mobility", 0)
            defense = data.get("defense", 0)
            base_attack = attack # 補正前の攻撃力

            # 属性一致ボーナスの適用
            if medal_attr == part_attr and medal_attr != "undefined":
                if medal_attr == "speed":
                    # スピード: 脚部の機動+20
                    if p_type == PartType.LEGS:
                        mobility += 20
                
                elif medal_attr == "power":
                    # パワー: 全パーツHP+5, 脚部以外の攻撃+5
                    hp += 5
                    if p_type != PartType.LEGS and attack is not None:
                        attack += 10
                        # base_attack は加算しない（時間計算への影響を避けるため）

                elif medal_attr == "technique":
                    # テクニック: 脚部以外の成功+10, 脚部の防御+20
                    if p_type == PartType.LEGS:
                        defense += 10
                    else:
                        success += 20

            parts[p_type] = BattleEntityFactory._create_part_entity(
                world, 
                p_type, 
                data.get("name", p_id), 
                hp, 
                data.get("trait"), 
                attack,
                base_attack,
                success,
                mobility,
                defense,
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
            # メダルとパーツをランダム風に取得
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