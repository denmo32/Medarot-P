"""ECSアーキテクチャに基づくバトルシステム構成"""

from core.ecs import World
from battle.entity_factory import BattleEntityFactory
from battle.systems.gauge_system import GaugeSystem
from battle.systems.combat_system import CombatSystem
from battle.systems.battle_status_system import BattleStatusSystem
from battle.systems.input_system import InputSystem
from battle.systems.render_system import RenderSystem
from ui.renderer import Renderer

class BattleSystem:
    """
    ECSワールドとシステムのコンテナ。
    """
    def __init__(self, screen,
                 player_count: int = 3, enemy_count: int = 3,
                 player_team_x: int = 50, enemy_team_x: int = 450,
                 team_y_offset: int = 100, character_spacing: int = 120,
                 gauge_width: int = 300, gauge_height: int = 40):
        
        self.world = World()

        # 1. コンポーネント生成（Factory使用）
        BattleEntityFactory.create_battle_context(self.world)
        BattleEntityFactory.create_input_manager(self.world)
        BattleEntityFactory.create_teams(
            self.world, player_count, enemy_count,
            player_team_x, enemy_team_x, team_y_offset, character_spacing,
            gauge_width, gauge_height
        )

        # 2. プレゼンテーション層の初期化
        self.renderer = Renderer(screen)

        # 3. システム初期化
        self.input_system = InputSystem(self.world)
        self.gauge_system = GaugeSystem(self.world)
        self.combat_system = CombatSystem(self.world)
        self.battle_status_system = BattleStatusSystem(self.world)
        # RenderSystemにRendererを注入
        self.render_system = RenderSystem(self.world, self.renderer)

    def update(self, dt: float = 0.016) -> None:
        """全システムの更新を実行"""
        self.input_system.update(dt)
        self.gauge_system.update(dt)
        self.combat_system.update(dt)
        self.battle_status_system.update(dt)
        # 描画システムの更新
        self.render_system.update(dt)