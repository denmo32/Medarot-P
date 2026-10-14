"""カスタマイズ画面のエントリーポイント（型付き遷移・一元化された入力処理）"""
from core.scene_manager import Scene, SceneTransition
from domain.constants import CustomizeState, SceneId
from features.customize.manager import CustomizeManager
from features.customize.view_builder import CustomizeViewBuilder
from ui.customize.layout import get_state_rects
from ui.customize.renderer import CustomizeRenderer
from ui.base.interaction import handle_menu_mouse


class CustomizeScene(Scene):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.manager = CustomizeManager(ctx.data_manager, ctx.save_manager)
        self.view_builder = CustomizeViewBuilder(ctx.data_manager, ctx.save_manager)
        self.renderer = CustomizeRenderer(self.screen)

    def handle_input(self, input_state) -> SceneTransition:
        if input_state.btn_menu:
            return SceneTransition.to(SceneId.TITLE)

        if input_state.mouse_clicked:
            model = self._build_model()
            layout = self.renderer.calc_layout(model)
            rects = get_state_rects(layout, self.manager.state)
            if rects:
                current_idx = self.manager.get_current_selection_index()
                new_idx, confirmed = handle_menu_mouse(
                    (input_state.mouse_x, input_state.mouse_y), True, rects, current_idx
                )
                if new_idx != current_idx:
                    self.manager.select_by_index(new_idx)
                if confirmed:
                    self.manager.confirm_current_selection()
                    return SceneTransition.stay()

        # キーボード入力のディスパッチ
        if input_state.btn_ok:
            self.manager.confirm_current_selection()
        elif input_state.btn_cancel:
            if self.manager.cancel_current_selection():
                return SceneTransition.to(SceneId.TITLE)
        elif self.manager.state == CustomizeState.ROBOT_SELECT:
            if input_state.btn_up:
                self.manager.move_robot_cursor(-1)
            elif input_state.btn_down:
                self.manager.move_robot_cursor(1)
        elif self.manager.state == CustomizeState.SLOT_SELECT:
            if input_state.btn_up:
                self.manager.move_slot_cursor(-1)
            elif input_state.btn_down:
                self.manager.move_slot_cursor(1)
            elif input_state.btn_left:
                self.manager.change_part_in_slot(-1)
            elif input_state.btn_right:
                self.manager.change_part_in_slot(1)
        elif self.manager.state == CustomizeState.PART_LIST_SELECT:
            if input_state.btn_up:
                self.manager.move_part_list_cursor(-1)
            elif input_state.btn_down:
                self.manager.move_part_list_cursor(1)

        return SceneTransition.stay()

    def _build_model(self):
        return self.view_builder.build(
            self.manager.state,
            self.manager.selected_robot_idx,
            self.manager.selected_slot_idx,
            self.manager.selected_part_list_idx,
            CustomizeManager.SLOTS,
        )

    def render(self):
        self.renderer.render(self._build_model())