"""カスタマイズ画面の状態管理と操作ロジック（UI/入力非依存の純粋ステートマシン）"""
from domain.config import PLAYER_COUNT
from domain.constants import CUSTOMIZE_SLOTS, CustomizeSlot, CustomizeState
from domain.models import GameDataProtocol, SaveDataProtocol


class CustomizeManager:
    SLOTS = CUSTOMIZE_SLOTS

    def __init__(self, data_manager: GameDataProtocol, save_manager: SaveDataProtocol):
        self.data_manager = data_manager
        self.save_data = save_manager
        self.state = CustomizeState.ROBOT_SELECT
        self.selected_robot_idx = 0
        self.selected_slot_idx = 0
        self.selected_part_list_idx = 0

    def get_current_selection_index(self) -> int:
        if self.state == CustomizeState.ROBOT_SELECT:
            return self.selected_robot_idx
        elif self.state == CustomizeState.SLOT_SELECT:
            return self.selected_slot_idx
        elif self.state == CustomizeState.PART_LIST_SELECT:
            return self.selected_part_list_idx
        return 0

    def select_by_index(self, index: int):
        if self.state == CustomizeState.ROBOT_SELECT:
            self.selected_robot_idx = index
        elif self.state == CustomizeState.SLOT_SELECT:
            self.selected_slot_idx = index
        elif self.state == CustomizeState.PART_LIST_SELECT:
            self.selected_part_list_idx = index

    def move_robot_cursor(self, delta: int):
        self.selected_robot_idx = (self.selected_robot_idx + delta) % PLAYER_COUNT

    def move_slot_cursor(self, delta: int):
        self.selected_slot_idx = (self.selected_slot_idx + delta) % len(self.SLOTS)

    def change_part_in_slot(self, direction: int):
        slot = self.SLOTS[self.selected_slot_idx]
        new_id = self._get_next_part_id(slot, direction)
        self.save_data.update_part(self.selected_robot_idx, slot, new_id)

    def move_part_list_cursor(self, delta: int):
        slot = self.SLOTS[self.selected_slot_idx]
        available_ids = self.data_manager.get_part_ids_for_type(slot)
        if available_ids:
            self.selected_part_list_idx = (self.selected_part_list_idx + delta) % len(available_ids)

    def confirm_current_selection(self):
        """現在の選択を確定して次の階層へ進む、または決定を反映する"""
        if self.state == CustomizeState.ROBOT_SELECT:
            self.state = CustomizeState.SLOT_SELECT
        elif self.state == CustomizeState.SLOT_SELECT:
            slot = self.SLOTS[self.selected_slot_idx]
            available_ids = self.data_manager.get_part_ids_for_type(slot)
            current_id = self._get_current_part_id(slot)
            self.selected_part_list_idx = available_ids.index(current_id) if current_id in available_ids else 0
            self.state = CustomizeState.PART_LIST_SELECT
        elif self.state == CustomizeState.PART_LIST_SELECT:
            slot = self.SLOTS[self.selected_slot_idx]
            available_ids = self.data_manager.get_part_ids_for_type(slot)
            if 0 <= self.selected_part_list_idx < len(available_ids):
                new_id = available_ids[self.selected_part_list_idx]
                self.save_data.update_part(self.selected_robot_idx, slot, new_id)
            self.state = CustomizeState.SLOT_SELECT

    def cancel_current_selection(self) -> bool:
        """キャンセル操作。最上位（ROBOT_SELECT）なら True（シーン離脱シグナル）を返す"""
        if self.state == CustomizeState.PART_LIST_SELECT:
            self.state = CustomizeState.SLOT_SELECT
            return False
        elif self.state == CustomizeState.SLOT_SELECT:
            self.state = CustomizeState.ROBOT_SELECT
            return False
        return True

    def _get_current_part_id(self, slot: CustomizeSlot) -> str:
        return self.save_data.get_part_id(self.selected_robot_idx, slot)

    def _get_next_part_id(self, slot: CustomizeSlot, direction: int = 1) -> str:
        current_id = self._get_current_part_id(slot)
        available_ids = self.data_manager.get_part_ids_for_type(slot)
        if not available_ids:
            return current_id
        if current_id not in available_ids:
            return available_ids[0]
        idx = available_ids.index(current_id)
        return available_ids[(idx + direction) % len(available_ids)]