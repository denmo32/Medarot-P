"""ECSアーキテクチャに基づくバトルシステム構成"""

from core.ecs import World
from battle.entity_factory import BattleEntityFactory
from battle.systems.gauge_system import GaugeSystem
from battle.systems.target_selection_system import TargetSelectionSystem
from battle.systems.turn_system import TurnSystem
from battle.systems.action_initiation_system import ActionInitiationSystem
from battle.systems.action_resolution_system import ActionResolutionSystem
from battle.systems.battle_flow_system import BattleFlowSystem
from battle.systems.damage_system import DamageSystem
from battle.systems.health_animation_system import HealthAnimationSystem
from battle.systems.battle_status_system import BattleStatusSystem
from battle.systems.input_system import InputSystem
from battle.systems.render_system import RenderSystem
from battle.systems.target_indicator_system import TargetIndicatorSystem
from battle.systems.cutin_animation_system import CutinAnimationSystem
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
        self.systems = [
            InputSystem(self.world),             # 1. 入力受付 (INPUT / ATTACK_DECLARATION)
            BattleFlowSystem(self.world),        # 2. 状態遷移管理
            GaugeSystem(self.world),             # 3. ゲージ進行
            TargetSelectionSystem(self.world),   # 4. ターゲット選定
            TurnSystem(self.world),              # 5. ターン管理
            ActionInitiationSystem(self.world),  # 6. 行動起案
            TargetIndicatorSystem(self.world),   # 7. ターゲット演出 (-> ATTACK_DECLARATION)
            CutinAnimationSystem(self.world),    # 8. カットイン演出 (-> EXECUTING)
            ActionResolutionSystem(self.world),  # 9. 行動解決
            DamageSystem(self.world),            # 10. ダメージ適用
            HealthAnimationSystem(self.world),   # 11. HPバーのアニメーション
            BattleStatusSystem(self.world),      # 12. 勝敗判定
            RenderSystem(self.world, self.renderer) # 13. 描画
        ]

    def update(self, dt: float = 0.016) -> None:
        for system in self.systems:
            system.update(dt)