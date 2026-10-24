"""バトル画面の描画オーケストレーション（ファサード）。"""
from ui_base.renderer import BaseRenderer
from features.battle.ui.renderers.command_menu_renderer import CommandMenuRenderer
from features.battle.ui.renderers.cutin_renderer import CutinRenderer
from features.battle.ui.renderers.field_renderer import FieldRenderer
from features.battle.ui.renderers.message_renderer import MessageRenderer
from features.battle.ui.renderers.overlay_renderer import OverlayRenderer
from features.battle.ui.renderers.robot_renderer import RobotRenderer
from features.battle.ui.renderers.status_panel_renderer import StatusPanelRenderer
from features.battle.ui.renderers.target_radar_renderer import TargetRadarRenderer
from features.battle.presentation.view_models import BattleRenderModel


class BattleRenderer(BaseRenderer):
    """バトル画面の描画順を制御するファサード"""

    def __init__(self, screen):
        super().__init__(screen)

        self.field_renderer = FieldRenderer(screen)
        self.status_panel_renderer = StatusPanelRenderer(screen)
        self.target_radar_renderer = TargetRadarRenderer(screen)
        self.robot_renderer = RobotRenderer(screen)
        self.message_renderer = MessageRenderer(screen)
        self.command_menu_renderer = CommandMenuRenderer(screen)
        self.cutin_renderer = CutinRenderer(screen)
        self.overlay_renderer = OverlayRenderer(screen)

    def render(self, model: BattleRenderModel):
        """表示モデルに従って 1 フレーム分の描画を行う"""
        self.clear()

        # 1. 画面上部ステータスパネル
        self.status_panel_renderer.render(model)

        # 2. フィールド・ロボット・レーダー
        self.field_renderer.render()
        self.robot_renderer.render(model)
        if model.target_radar is not None:
            self.target_radar_renderer.render(model)

        # 3. メッセージウィンドウ
        if model.message_window is not None:
            self.message_renderer.render(model.message_window)

        # 4. コマンドメニュー
        if model.command_menu is not None:
            self.command_menu_renderer.render(model.command_menu)

        # 5. カットイン演出
        if model.cutin is not None:
            self.cutin_renderer.render(model.cutin)

        # 6. オーバーレイ（開幕演出・勝敗表示）
        self.overlay_renderer.render(model)

        self.present()