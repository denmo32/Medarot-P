"""
ECS Systemとして動作する描画コントローラー
ViewModelを使ってSnapshotを生成し、Rendererに渡す。
"""

from core.ecs import System
from .view_model import BattleViewModel
from .renderer import BattleRenderer

class BattleRenderSystem(System):
    """描画パイプラインの駆動役"""
    
    def __init__(self, world, screen, view_model=None):
        super().__init__(world)
        # 指定がなければ自身で生成するが、通常はOrchestratorから共有される
        self.view_model = view_model if view_model else BattleViewModel(world)
        self.renderer = BattleRenderer(screen)

    def update(self, dt: float):
        # 1. 現在の画面サイズを取得
        screen_size = self.renderer.get_screen_size()
        
        # 2. 状態のスナップショットを生成（ロジック層に画面サイズを渡す）
        snapshot = self.view_model.create_snapshot(screen_size)
        
        # 3. レンダラーに描画させる
        self.renderer.render(snapshot)