"""
バトルシーンの描画を統括するレンダラー
各専門レンダラー（Field, UI, Cutin）を組み合わせて画面を構成する。
"""

from ui.base.renderer import BaseRenderer
from ui.base.widgets import MedabotWidgets
from .snapshot import BattleStateSnapshot
from .field_renderer import FieldRenderer
from .panel_renderer import UIPanelRenderer
from .cutin_renderer import CutinRenderer

class BattleRenderer(BaseRenderer):
    """メインの描画パイプライン"""

    def __init__(self, screen):
        super().__init__(screen)
        self.widgets = MedabotWidgets(self)
        
        # サブレンダラーに処理を委譲
        self.field = FieldRenderer(self)
        self.ui_panel = UIPanelRenderer(self)
        self.cutin = CutinRenderer(self)

    def render(self, snapshot: BattleStateSnapshot):
        """1フレームを描画。レイヤーの順序を制御する。"""
        self.clear()
        
        # 下層：フィールド（機体位置、軌跡など）
        self.field.render(snapshot)
        
        # 中層：UIパネル（メッセージ、メニュー）
        self.ui_panel.render(snapshot)

        # 上層：カットイン（演出発生時のみ）
        if snapshot.cutin.is_active:
            self.cutin.render(snapshot.cutin)

        self.present()