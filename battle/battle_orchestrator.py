"""ECSアーキテクチャに基づくバトルシステム構成"""

from core.ecs import World
from battle.battle_entity_factory import BattleEntityFactory
from domain.config import PLAYER_COUNT, ENEMY_COUNT
from data.game_data_manager import GameDataManager
from data.save_data_manager import SaveDataManager

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

class BattleEngine:
    def __init__(self, 
                 data_manager: GameDataManager,
                 save_manager: SaveDataManager,
                 ui_params: dict,
                 player_count: int = PLAYER_COUNT, 
                 enemy_count: int = ENEMY_COUNT):
        
        self.data_manager = data_manager
        self.save_manager = save_manager

        self.world = World()
        BattleEntityFactory.create_battle_context(self.world)
        BattleEntityFactory.create_input_manager(self.world)
        
        # UI設定から比率パラメータを渡す（外部から注入されたui_paramsを使用）
        BattleEntityFactory.create_teams(self.world, player_count, enemy_count,
            ui_params['PLAYER_TEAM_X_RATIO'], 
            ui_params['ENEMY_TEAM_X_RATIO'],
            ui_params['TEAM_Y_START_RATIO'], 
            ui_params['CHAR_SPACING_RATIO'],
            self.data_manager, self.save_manager
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
            BattleStatusSystem(self.world)
        ]

    def update(self, dt: float = 0.016) -> None:
        for system in self.systems:
            system.update(dt)