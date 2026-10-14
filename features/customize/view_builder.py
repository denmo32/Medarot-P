"""カスタマイズ画面の View Model 構築クラス（RobotSetup 対応）"""
from typing import Optional, Tuple, Union, TYPE_CHECKING
from domain.config import PLAYER_COUNT
from domain.constants import PART_TYPE_LABELS, CustomizeState, PartType, CustomizeSlot
from domain.models import MedalData, PartData
from features.customize.view_models import (
    CustomizeDetailPanelModel,
    CustomizeDetailStatModel,
    CustomizePartListItemModel,
    CustomizeSlotItemModel,
    CustomizeViewModel,
)

if TYPE_CHECKING:
    from data.game_data_manager import GameDataManager
    from data.save_data_manager import SaveDataManager

DetailData = Union[PartData, MedalData]


class CustomizeViewBuilder:
    def __init__(self, data_manager: 'GameDataManager', save_manager: 'SaveDataManager'):
        self.data_manager = data_manager
        self.save_data = save_manager

    def build(
        self,
        state: CustomizeState,
        selected_robot_idx: int,
        selected_slot_idx: int,
        selected_part_list_idx: int,
        slots_def: Tuple[CustomizeSlot, ...],
    ) -> CustomizeViewModel:
        current_state = CustomizeState.from_key(state) or CustomizeState.ROBOT_SELECT
        setup = self.save_data.get_robot_setup(selected_robot_idx)
        slot = slots_def[selected_slot_idx]

        focused_id = self._resolve_focused_id(current_state, slot, selected_robot_idx, selected_part_list_idx)
        focused_data = self._resolve_focused_data(focused_id)

        slots = [
            CustomizeSlotItemModel(
                label=PART_TYPE_LABELS.get(s, s.value),
                part_name=self.data_manager.get_part_name(
                    self.save_data.get_part_id(selected_robot_idx, s)
                ),
                is_selected=(current_state != CustomizeState.ROBOT_SELECT and selected_slot_idx == i),
            )
            for i, s in enumerate(slots_def)
        ]

        available_ids = self.data_manager.get_part_ids_for_type(slot)
        part_list = [
            CustomizePartListItemModel(
                name=self.data_manager.get_part_name(pid),
                is_focused=(current_state == CustomizeState.PART_LIST_SELECT and selected_part_list_idx == i),
            )
            for i, pid in enumerate(available_ids)
        ]

        robot_names = [f"機体{i+1}" for i in range(PLAYER_COUNT)]
        detail = self._build_detail_model(slot, focused_data)

        return CustomizeViewModel(
            state=current_state,
            robot_names=robot_names,
            selected_robot_idx=selected_robot_idx,
            active_robot_name=setup.name if setup else f"機体{selected_robot_idx+1}",
            slots=slots,
            selected_slot_idx=selected_slot_idx,
            part_list=part_list,
            selected_part_list_idx=selected_part_list_idx,
            detail=detail,
        )

    def _resolve_focused_id(
        self, state: CustomizeState, slot: CustomizeSlot, robot_idx: int, part_list_idx: int
    ) -> str:
        if state == CustomizeState.PART_LIST_SELECT:
            available_ids = self.data_manager.get_part_ids_for_type(slot)
            if available_ids:
                return available_ids[part_list_idx % len(available_ids)]
        return self.save_data.get_part_id(robot_idx, slot)

    def _resolve_focused_data(self, focused_id: str) -> Optional[DetailData]:
        part_data = self.data_manager.get_part_data(focused_id)
        return part_data if part_data is not None else self.data_manager.get_medal_data(focused_id)

    def _build_detail_model(
        self, slot: CustomizeSlot, focused_data: Optional[DetailData]
    ) -> Optional[CustomizeDetailPanelModel]:
        if focused_data is None:
            return None
        if isinstance(focused_data, MedalData):
            return self._build_medal_detail(focused_data)
        return self._build_part_detail(slot, focused_data)

    def _build_medal_detail(self, medal: MedalData) -> CustomizeDetailPanelModel:
        return CustomizeDetailPanelModel(
            title="メダル詳細",
            name=medal.name,
            stats=[
                CustomizeDetailStatModel("ニックネーム", medal.nickname or "-"),
                CustomizeDetailStatModel("性格", medal.personality.display_name),
                CustomizeDetailStatModel("属性", medal.attribute.display_name),
            ],
        )

    def _build_part_detail(self, slot: CustomizeSlot, part: PartData) -> CustomizeDetailPanelModel:
        attr_label = part.attribute.display_name
        if slot.part_type == PartType.LEGS:
            stats = [
                CustomizeDetailStatModel("属性", attr_label),
                CustomizeDetailStatModel("装甲", str(part.hp)),
                CustomizeDetailStatModel("機動", str(part.mobility)),
                CustomizeDetailStatModel("防御", str(part.defense)),
            ]
        else:
            stats = [
                CustomizeDetailStatModel("属性", attr_label),
                CustomizeDetailStatModel("装甲", str(part.hp)),
                CustomizeDetailStatModel("成功", str(part.success)),
                CustomizeDetailStatModel("威力", str(part.attack) if part.attack is not None else "---"),
            ]
        return CustomizeDetailPanelModel(title="パーツ詳細", name=part.name, stats=stats)