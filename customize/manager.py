"""カスタマイズ画面のロジック管理"""

from data.save_data_manager import get_save_manager
from data.parts_data_manager import get_parts_manager

class CustomizeManager:
    """カスタマイズ画面の状態管理と操作ロジック"""
    
    # 状態定義
    STATE_MACHINE_SELECT = "machine_select"
    STATE_SLOT_SELECT = "slot_select"
    STATE_PART_LIST_SELECT = "part_list_select"

    def __init__(self):
        self.save_data = get_save_manager()
        self.parts_manager = get_parts_manager()
        
        self.state = self.STATE_MACHINE_SELECT
        self.selected_machine_idx = 0
        self.selected_slot_idx = 0  # 0:medal, 1:head, 2:r_arm, 3:l_arm, 4:legs
        self.selected_part_list_idx = 0
        
        self.slots = ["medal", "head", "right_arm", "left_arm", "legs"]

    def handle_input(self, input_comp) -> str:
        """入力を処理し、遷移アクションがあれば返す"""
        
        if self.state == self.STATE_MACHINE_SELECT:
            return self._handle_machine_select(input_comp)
        
        elif self.state == self.STATE_SLOT_SELECT:
            return self._handle_slot_select(input_comp)
            
        elif self.state == self.STATE_PART_LIST_SELECT:
            return self._handle_part_list_select(input_comp)
            
        return None

    def _handle_machine_select(self, input_comp):
        if input_comp.key_up:
            self.selected_machine_idx = (self.selected_machine_idx - 1) % 3
        elif input_comp.key_down:
            self.selected_machine_idx = (self.selected_machine_idx + 1) % 3
        elif input_comp.key_z:
            self.state = self.STATE_SLOT_SELECT
        elif input_comp.key_x or input_comp.escape_pressed:
            # タイトルへ戻る
            return "title"
        return None

    def _handle_slot_select(self, input_comp):
        if input_comp.key_up:
            self.selected_slot_idx = (self.selected_slot_idx - 1) % len(self.slots)
        elif input_comp.key_down:
            self.selected_slot_idx = (self.selected_slot_idx + 1) % len(self.slots)
        
        # 左右キーでクイック切り替え
        elif input_comp.key_left or input_comp.key_right:
            direction = 1 if input_comp.key_right else -1
            slot_name = self.slots[self.selected_slot_idx]
            current_setup = self.save_data.get_machine_setup(self.selected_machine_idx)
            
            # ID取得
            if slot_name == "medal":
                current_id = current_setup["medal"]
            else:
                current_id = current_setup["parts"][slot_name]
            
            new_id = self.parts_manager.get_next_part_id(current_id, direction)
            self.save_data.update_part(self.selected_machine_idx, slot_name, new_id)

        elif input_comp.key_z:
            # リスト選択へ
            slot_name = self.slots[self.selected_slot_idx]
            available_ids = self.parts_manager.get_part_ids_for_type(slot_name)
            current_setup = self.save_data.get_machine_setup(self.selected_machine_idx)
            
            if slot_name == "medal":
                current_id = current_setup["medal"]
            else:
                current_id = current_setup["parts"][slot_name]
                
            self.selected_part_list_idx = available_ids.index(current_id) if current_id in available_ids else 0
            self.state = self.STATE_PART_LIST_SELECT
            
        elif input_comp.key_x or input_comp.escape_pressed:
            self.state = self.STATE_MACHINE_SELECT
        return None

    def _handle_part_list_select(self, input_comp):
        slot_name = self.slots[self.selected_slot_idx]
        available_ids = self.parts_manager.get_part_ids_for_type(slot_name)
        
        if input_comp.key_up:
            self.selected_part_list_idx = (self.selected_part_list_idx - 1) % len(available_ids)
        elif input_comp.key_down:
            self.selected_part_list_idx = (self.selected_part_list_idx + 1) % len(available_ids)
        elif input_comp.key_z:
            # アイテム決定
            new_id = available_ids[self.selected_part_list_idx]
            self.save_data.update_part(self.selected_machine_idx, slot_name, new_id)
            self.state = self.STATE_SLOT_SELECT
        elif input_comp.key_x or input_comp.escape_pressed:
            self.state = self.STATE_SLOT_SELECT
        return None

    def get_ui_data(self):
        """描画に必要な現在のデータを整理して返す"""
        setup = self.save_data.get_machine_setup(self.selected_machine_idx)
        slot_name = self.slots[self.selected_slot_idx]
        
        if slot_name == "medal":
            focused_id = setup["medal"]
        else:
            focused_id = setup["parts"][slot_name]
        
        # リスト選択中の場合はリストのものをフォーカス
        if self.state == self.STATE_PART_LIST_SELECT:
            available_ids = self.parts_manager.get_part_ids_for_type(slot_name)
            focused_id = available_ids[self.selected_part_list_idx]

        # 詳細データ取得（メダルかパーツか）
        focused_data = self.parts_manager.get_part_data(focused_id)
        if not focused_data:
            focused_data = self.parts_manager.get_medal_data(focused_id)

        return {
            "state": self.state,
            "machine_idx": self.selected_machine_idx,
            "slot_idx": self.selected_slot_idx,
            "part_list_idx": self.selected_part_list_idx,
            "machine_name": setup["name"],
            "setup": setup,
            "focused_id": focused_id,
            "focused_data": focused_data,
            "available_ids": self.parts_manager.get_part_ids_for_type(slot_name)
        }