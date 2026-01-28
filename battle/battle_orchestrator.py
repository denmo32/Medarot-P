"""ECSアーキテクチャに基づくバトルシステム構成"""

from core.ecs import World
from battle.battle_entity_factory import BattleEntityFactory

# Systems (Logic)
from battle.systems.action.gauge_system import GaugeSystem
from battle.systems.action.interruption_system import InterruptionSystem
from battle.systems.action.target_selection_system import TargetSelectionSystem
from battle.systems.flow.turn_system import TurnSystem
from battle.systems.ai.ai_system import AISystem
from battle.systems.action.action_command_system import ActionCommandSystem
from battle.systems.action.action_initiation_system import ActionInitiationSystem
from battle.systems.action.action_resolution_system import ActionResolutionSystem
from battle.systems.flow.battle_flow_system import BattleFlowSystem
from battle.systems.action.damage_system import DamageSystem
from battle.systems.action.destruction_system import DestructionSystem
from battle.systems.flow.battle_status_system import BattleStatusSystem
from battle.systems.input.input_system import InputSystem
from battle.systems.flow.target_indicator_system import TargetIndicatorSystem
from battle.systems.flow.cutin_flow_system import CutinFlowSystem

# Systems (UI Layer)
from ui.battle.visual_systems import HealthAnimationSystem
from ui.battle.system import BattleRenderSystem

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
        
        self.systems = [
            InputSystem(self.world),
            BattleFlowSystem(self.world),
            InterruptionSystem(self.world), # ゲージ進行の前に中断を確認
            GaugeSystem(self.world),
            TargetSelectionSystem(self.world),
            TurnSystem(self.world),
            AISystem(self.world),
            ActionCommandSystem(self.world),
            ActionInitiationSystem(self.world),
            TargetIndicatorSystem(self.world),
            CutinFlowSystem(self.world),
            ActionResolutionSystem(self.world),
            DamageSystem(self.world),
            DestructionSystem(self.world),
            BattleStatusSystem(self.world),
            
            # UI系システム
            HealthAnimationSystem(self.world),
            BattleRenderSystem(self.world, screen)
        ]

    def update(self, dt: float = 0.016) -> None:
        for system in self.systems:
            system.update(dt)