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

    # === 描画オーケストレーション ===

    def render(self, model: BattleRenderModel):
        """表示モデルに従って 1 フレーム分の描画を行う"""
        self.clear()

        if model.top_status is not None:
            self.status_panel_renderer.render(model.top_status)

        if model.show_field:
            self.field_renderer.render()
            self.robot_renderer.render(model)
            self.target_radar_renderer.render(model)

        if model.show_message_window and model.message_window is not None:
            self.message_renderer.render(model.message_window)

        if model.show_command_menu and model.command_menu is not None:
            self.command_menu_renderer.render(model.command_menu)

        if model.show_cutin and model.cutin is not None:
            self.cutin_renderer.render(model.cutin)

        if model.overlay is not None:
            self.overlay_renderer.render(model.overlay)

        self.present()