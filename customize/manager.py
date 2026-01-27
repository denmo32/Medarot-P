"""カスタマイズ画面のロジック管理"""

from data.save_data_manager import get_save_manager
from data.game_data_manager import get_game_data_manager

class CustomizeManager:
    """カスタマイズ画面の状態管理と操作ロジック"""
    
    STATE_MACHINE_SELECT = "machine_select"
    STATE_SLOT_SELECT = "slot_select"
    STATE_PART_LIST_SELECT = "part_list_select"

    def __init__(self):
        self.save_data = get_save_manager()
        self.data_manager = get_game_data_manager()
        self.state = self.STATE_MACHINE_SELECT
        self.selected_machine_idx = 0
        self.selected_slot_idx = 0
        self.selected_part_list_idx = 0
        self.slots = ["medal", "head", "right_arm", "left_arm", "legs"]

    def handle_input(self, input_comp) -> str:
        if self.state == self.STATE_MACHINE_SELECT:
            return self._handle_machine_select(input_comp)
        elif self.state == self.STATE_SLOT_SELECT:
            return self._handle_slot_select(input_comp)
        elif self.state == self.STATE_PART_LIST_SELECT:
            return self._handle_part_list_select(input_comp)
        return None

    def _handle_machine_select(self, input_comp):
        if input_comp.btn_up: self.selected_machine_idx = (self.selected_machine_idx - 1) % 3
        elif input_comp.btn_down: self.selected_machine_idx = (self.selected_machine_idx + 1) % 3
        elif input_comp.btn_ok: self.state = self.STATE_SLOT_SELECT
        elif input_comp.btn_cancel or input_comp.btn_menu: return "title"
        return None

    def _handle_slot_select(self, input_comp):
        if input_comp.btn_up: self.selected_slot_idx = (self.selected_slot_idx - 1) % len(self.slots)
        elif input_comp.btn_down: self.selected_slot_idx = (self.selected_slot_idx + 1) % len(self.slots)
        elif input_comp.btn_left or input_comp.btn_right:
            direction = 1 if input_comp.btn_right else -1
            slot_name = self.slots[self.selected_slot_idx]
            current_id = self._get_current_part_id(slot_name)
            new_id = self.data_manager.get_next_part_id(current_id, direction)
            self.save_data.update_part(self.selected_machine_idx, slot_name, new_id)
        elif input_comp.btn_ok:
            slot_name = self.slots[self.selected_slot_idx]
            available_ids = self.data_manager.get_part_ids_for_type(slot_name)
            current_id = self._get_current_part_id(slot_name)
            self.selected_part_list_idx = available_ids.index(current_id) if current_id in available_ids else 0
            self.state = self.STATE_PART_LIST_SELECT
        elif input_comp.btn_cancel or input_comp.btn_menu:
            self.state = self.STATE_MACHINE_SELECT
        return None

    def _handle_part_list_select(self, input_comp):
        slot_name = self.slots[self.selected_slot_idx]
        available_ids = self.data_manager.get_part_ids_for_type(slot_name)
        if input_comp.btn_up: self.selected_part_list_idx = (self.selected_part_list_idx - 1) % len(available_ids)
        elif input_comp.btn_down: self.selected_part_list_idx = (self.selected_part_list_idx + 1) % len(available_ids)
        elif input_comp.btn_ok:
            new_id = available_ids[self.selected_part_list_idx]
            self.save_data.update_part(self.selected_machine_idx, slot_name, new_id)
            self.state = self.STATE_SLOT_SELECT
        elif input_comp.btn_cancel or input_comp.btn_menu:
            self.state = self.STATE_SLOT_SELECT
        return None

    def _get_current_part_id(self, slot_name):
        current_setup = self.save_data.get_machine_setup(self.selected_machine_idx)
        return current_setup["medal"] if slot_name == "medal" else current_setup["parts"][slot_name]

    def get_ui_data(self):
        """描画に必要なデータを解決済みの状態で生成する"""
        setup = self.save_data.get_machine_setup(self.selected_machine_idx)
        slot_name = self.slots[self.selected_slot_idx]
        
        # 1. スロット情報の事前構築
        slots_info = []
        for s_name in self.slots:
            item_id = setup["medal"] if s_name == "medal" else setup["parts"][s_name]
            slots_info.append({
                'label': self.data_manager.PART_TYPE_LABELS.get(s_name, s_name),
                'part_name': self.data_manager.get_part_name(item_id)
            })

        # 2. フォーカスデータの取得
        if self.state == self.STATE_PART_LIST_SELECT:
            available_ids = self.data_manager.get_part_ids_for_type(slot_name)
            focused_id = available_ids[self.selected_part_list_idx]
        else:
            focused_id = self._get_current_part_id(slot_name)

        focused_data = self.data_manager.get_part_data(focused_id) or self.data_manager.get_medal_data(focused_id)
        attr_label = self.data_manager.get_attribute_label(focused_data.get('attribute', 'undefined'))

        # 3. リスト情報の事前構築
        available_ids = self.data_manager.get_part_ids_for_type(slot_name)
        available_list = [{'name': self.data_manager.get_part_name(pid)} for pid in available_ids]

        # 4. メダル属性（ボーナス判定用）
        medal_data = self.data_manager.get_medal_data(setup["medal"])
        current_medal_attr = medal_data.get("attribute", "undefined")

        return {
            "state": self.state,
            "machine_idx": self.selected_machine_idx,
            "slot_idx": self.selected_slot_idx,
            "part_list_idx": self.selected_part_list_idx,
            "machine_name": setup["name"],
            "slots_info": slots_info,
            "available_list": available_list,
            "focused_data": focused_data,
            "focused_attr_label": attr_label,
            "current_medal_attr": current_medal_attr
        }