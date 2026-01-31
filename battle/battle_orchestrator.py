"""ECSアーキテクチャに基づくバトルシステム構成"""

from core.ecs import World
from battle.battle_entity_factory import BattleEntityFactory
from domain.config import PLAYER_COUNT, ENEMY_COUNT
from ui.config import UI_PARAMS

# Systems (Logic)
# Decision
from battle.systems.decision.input_system import InputSystem
from battle.systems.decision.ai_system import AISystem
from battle.systems.decision.target_selection_system import TargetSelectionSystem
# Unit
from battle.systems.unit.gauge_system import GaugeSystem
# Flow
from battle.systems.flow.turn_system import TurnSystem
from battle.systems.flow.battle_flow_system import BattleFlowSystem
from battle.systems.flow.battle_status_system import BattleStatusSystem
from battle.systems.flow.target_indicator_system import TargetIndicatorSystem
from battle.systems.flow.cutin_flow_system import CutinFlowSystem
# Action
from battle.systems.action.action_command_system import ActionCommandSystem
from battle.systems.action.action_initiation_system import ActionInitiationSystem
from battle.systems.action.action_resolution_system import ActionResolutionSystem
# Impact
from battle.systems.impact.damage_system import DamageSystem
from battle.systems.impact.destruction_system import DestructionSystem

# ViewModel and Systems (UI Layer)
from ui.battle.view_model import BattleViewModel
from ui.battle.visual_systems import HealthAnimationSystem
from ui.battle.system import BattleRenderSystem

class BattleSystem:
    def __init__(self, screen, 
                 player_count: int = PLAYER_COUNT, 
                 enemy_count: int = ENEMY_COUNT,
                 player_team_x: int = UI_PARAMS['PLAYER_TEAM_X'], 
                 enemy_team_x: int = UI_PARAMS['ENEMY_TEAM_X'],
                 team_y_offset: int = UI_PARAMS['TEAM_Y_OFFSET'], 
                 character_spacing: int = UI_PARAMS['CHARACTER_SPACING'],
                 gauge_width: int = UI_PARAMS['GAUGE_WIDTH'], 
                 gauge_height: int = UI_PARAMS['GAUGE_HEIGHT']):
        
        self.world = World()
        BattleEntityFactory.create_battle_context(self.world)
        BattleEntityFactory.create_input_manager(self.world)
        BattleEntityFactory.create_teams(self.world, player_count, enemy_count,
            player_team_x, enemy_team_x, team_y_offset, character_spacing,
            gauge_width, gauge_height
        )
        
        # 描画と入力解釈で共有するViewModelを生成
        self.view_model = BattleViewModel(self.world)
        
        self.systems = [
            InputSystem(self.world, self.view_model),
            BattleFlowSystem(self.world),
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
            BattleRenderSystem(self.world, screen, self.view_model)
        ]

    def update(self, dt: float = 0.016) -> None:
        for system in self.systems:
            system.update(dt)