"""ECSアーキテクチャに基づくバトルシステム構成"""

from core.ecs import World
from battle.entity_factory import BattleEntityFactory
from battle.systems.action.gauge_system import GaugeSystem
from battle.systems.action.target_selection_system import TargetSelectionSystem
from battle.systems.flow.turn_system import TurnSystem
from battle.systems.ai.ai_system import AISystem
from battle.systems.action.action_initiation_system import ActionInitiationSystem
from battle.systems.action.action_resolution_system import ActionResolutionSystem
from battle.systems.flow.battle_flow_system import BattleFlowSystem
from battle.systems.action.damage_system import DamageSystem
from battle.systems.presentation.health_animation_system import HealthAnimationSystem
from battle.systems.flow.battle_status_system import BattleStatusSystem
from battle.systems.input.input_system import InputSystem
from battle.systems.presentation.render_system import RenderSystem
from battle.systems.presentation.target_indicator_system import TargetIndicatorSystem
from battle.systems.presentation.cutin_animation_system import CutinAnimationSystem
from ui.field_renderer import FieldRenderer
from ui.battle_ui_renderer import BattleUIRenderer

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

        self.field_renderer = FieldRenderer(screen)
        self.ui_renderer = BattleUIRenderer(screen)
        
        self.systems = [
            # ui_renderer を InputSystem に渡すように変更
            InputSystem(self.world, self.ui_renderer),
            BattleFlowSystem(self.world),
            GaugeSystem(self.world),
            TargetSelectionSystem(self.world),
            TurnSystem(self.world),
            AISystem(self.world),
            ActionInitiationSystem(self.world),
            TargetIndicatorSystem(self.world),
            CutinAnimationSystem(self.world),
            ActionResolutionSystem(self.world),
            DamageSystem(self.world),
            HealthAnimationSystem(self.world),
            BattleStatusSystem(self.world),
            RenderSystem(self.world, self.field_renderer, self.ui_renderer)
        ]

    def update(self, dt: float = 0.016) -> None:
        for system in self.systems:
            system.update(dt)