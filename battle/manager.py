"""ECSアーキテクチャに基づくバトルシステム構成"""

from core.ecs import World
from battle.entity_factory import BattleEntityFactory
from battle.systems.gauge_system import GaugeSystem
from battle.systems.target_selection_system import TargetSelectionSystem
from battle.systems.turn_system import TurnSystem
from battle.systems.action_execution_system import ActionExecutionSystem
from battle.systems.damage_system import DamageSystem
from battle.systems.battle_status_system import BattleStatusSystem
from battle.systems.input_system import InputSystem
from battle.systems.render_system import RenderSystem
from ui.renderer import Renderer

class BattleSystem:
    def __init__(self, screen, player_count: int = 3, enemy_count: int = 3,
                 player_team_x: int = 50, enemy_team_x: int = 450,
                 team_y_offset: int = 100, character_spacing: int = 120,
                 gauge_width: int = 300, gauge_height: int = 40):
        
        self.world = World()
        BattleEntityFactory.create_battle_context(self.world)
        BattleEntityFactory.create_input_manager(self.world)
        BattleEntityFactory.create_teams(self.world, player_count, enemy_count,
            player_team_x, enemy_team_x, team_y_offset, character_spacing,
            gauge_width, gauge_height
        )

        self.renderer = Renderer(screen)
        
        # システム更新順序を整理
        # AISystemをTurnSystemに統合し、プレイヤーのターン開始も管理
        self.systems = [
            InputSystem(self.world),
            GaugeSystem(self.world),
            TargetSelectionSystem(self.world),
            TurnSystem(self.world),
            ActionExecutionSystem(self.world),
            DamageSystem(self.world),
            BattleStatusSystem(self.world),
            RenderSystem(self.world, self.renderer)
        ]

    def update(self, dt: float = 0.016) -> None:
        for system in self.systems:
            system.update(dt)