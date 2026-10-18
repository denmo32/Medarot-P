"""カスタマイズ画面のエントリーポイント（型付き遷移・一元化された入力処理・ヘッドレス両対応）"""
from core.scene_manager import Scene, SceneTransition
from core.constants import SceneId
from domain.constants import CustomizeState
from features.customize.manager import CustomizeManager
from features.customize.view_builder import CustomizeViewBuilder
from ui.customize.layout import hit_test_customize
from ui.customize.renderer import CustomizeRenderer


class CustomizeScene(Scene):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.manager = CustomizeManager(ctx.data_manager, ctx.save_manager)
        self.view_builder = CustomizeViewBuilder(ctx.data_manager, ctx.save_manager)
        self.renderer = CustomizeRenderer(self.screen) if self.screen is not None else None

    def handle_input(self, input_state) -> SceneTransition:
        if input_state.btn_menu:
            return SceneTransition.to(SceneId.TITLE)

        if input_state.mouse_clicked and self.screen is not None:
            sw, sh = self.screen.get_size()
            current_idx = self.manager.get_current_selection_index()
            # レイアウト計算用の最小限のモデルを取得して判定
            model = self._build_model()
            new_idx, confirmed = hit_test_customize(
                (sw, sh),
                (input_state.mouse_x, input_state.mouse_y),
                self.manager.state,
                current_idx,
                model,
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
        if self.renderer is not None:
            self.renderer.render(self._build_model())