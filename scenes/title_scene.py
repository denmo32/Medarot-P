"""タイトル画面の実装（型付き遷移・ViewModel対応）"""
from core.scene_manager import Scene, SceneTransition
from domain.constants import SceneId
from features.title.view_models import TitleButtonModel, TitleViewModel
from ui.title.renderer import TitleRenderer, calculate_button_layouts
from ui.base.interaction import handle_menu_mouse


class TitleScene(Scene):
    BUTTON_CONFIGS = (
        ('バトル開始', SceneId.BATTLE, 0.5, 0.55, 0.25, 0.1),
        ('カスタマイズ', SceneId.CUSTOMIZE, 0.5, 0.68, 0.25, 0.1),
    )

    def __init__(self, ctx):
        super().__init__(ctx)
        self.renderer = TitleRenderer(self.screen)
        self.selected_index = 0

    def _build_model(self) -> TitleViewModel:
        buttons = [
            TitleButtonModel(
                text=text,
                target=target,
                cx=cx,
                cy=cy,
                w_ratio=w,
                h_ratio=h,
                is_selected=(i == self.selected_index),
            )
            for i, (text, target, cx, cy, w, h) in enumerate(self.BUTTON_CONFIGS)
        ]
        return TitleViewModel(buttons=buttons, selected_index=self.selected_index)

    def handle_input(self, input_state) -> SceneTransition:
        model = self._build_model()
        button_count = len(model.buttons)

        if input_state.btn_up:
            self.selected_index = (self.selected_index - 1) % button_count
        elif input_state.btn_down:
            self.selected_index = (self.selected_index + 1) % button_count
        elif input_state.btn_ok:
            return SceneTransition.to(model.buttons[self.selected_index].target)
        elif input_state.btn_menu:
            return SceneTransition.quit()

        if input_state.mouse_clicked:
            sw, sh = self.renderer.get_screen_size()
            layouts = calculate_button_layouts((sw, sh), model.buttons)
            self.selected_index, confirmed = handle_menu_mouse(
                (input_state.mouse_x, input_state.mouse_y),
                True,
                layouts,
                self.selected_index,
            )
            if confirmed:
                return SceneTransition.to(model.buttons[self.selected_index].target)

        return SceneTransition.stay()

    def render(self):
        self.renderer.render(self._build_model())