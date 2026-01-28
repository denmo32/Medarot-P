"""
ECS Systemとして動作する描画コントローラー
ViewModelを使ってSnapshotを生成し、Rendererに渡す。
"""

from core.ecs import System
from .view_model import BattleViewModel
from .renderer import BattleRenderer

class BattleRenderSystem(System):
    """描画パイプラインの駆動役"""
    
    def __init__(self, world, screen):
        super().__init__(world)
        self.view_model = BattleViewModel(world)
        self.renderer = BattleRenderer(screen)

    def update(self, dt: float):
        # 1. 状態のスナップショットを生成
        snapshot = self.view_model.create_snapshot()
        
        # 2. レンダラーに描画させる
        self.renderer.render(snapshot)