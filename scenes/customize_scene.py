"""カスタマイズ画面のエントリーポイント"""

from customize.manager import CustomizeManager
from ui.customize_renderer import CustomizeRenderer
from input.event_manager import EventManager
from core.ecs import World

class CustomizeScene:
    """カスタマイズ画面のシーンクラス"""

    def __init__(self, screen):
        self.screen = screen
        # ロジック・描画の分離
        self.manager = CustomizeManager()
        self.renderer = CustomizeRenderer(screen)
        
        # 入力管理用に一時的なWorldを作成
        self.world = World()
        self.event_manager = EventManager(self.world)

    def handle_events(self):
        """イベント処理"""
        if not self.event_manager.handle_events():
            return 'quit'
        
        input_comp = self.world.entities[self.event_manager.input_entity_id]['input']
        return self.manager.handle_input(input_comp)

    def update(self, dt):
        """更新処理（現在は特になし）"""
        pass

    def render(self):
        """描画処理"""
        ui_data = self.manager.get_ui_data()
        self.renderer.render(ui_data)
        self.renderer.present()