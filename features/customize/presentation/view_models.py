"""カスタマイズ画面の表示専用データ構造（View Model）。"""
from dataclasses import dataclass, field
from typing import List, Optional
from domain.constants import CustomizeState


@dataclass(frozen=True)
class CustomizeSlotItemModel:
    """スロット 1 行分の表示情報"""
    label: str          # "メダル", "頭部", "右腕", etc.
    part_name: str      # 装着中のパーツ名
    is_selected: bool   # 選択枠ハイライト対象か


@dataclass(frozen=True)
class CustomizePartListItemModel:
    """パーツ一覧の 1 行分の表示情報"""
    name: str           # パーツ名
    is_focused: bool    # リスト内でフォーカスされているか


@dataclass(frozen=True)
class CustomizeDetailStatModel:
    """詳細情報パネルのステータス 1 行分（ラベルと値のフラットなペア）"""
    label: str          # "属性", "装甲", "機動", "威力", etc.
    value: str          # "スピード", "50", "35", "---", etc.


@dataclass(frozen=True)
class CustomizeDetailPanelModel:
    """右側詳細情報パネルの表示情報"""
    title: str          # "メダル詳細" または "パーツ詳細"
    name: str           # パーツ名またはメダル名
    stats: List[CustomizeDetailStatModel] = field(default_factory=list)


@dataclass(frozen=True)
class CustomizeViewModel:
    """カスタマイズ画面 1 フレーム分の描画用統一モデル"""
    state: CustomizeState
    robot_names: List[str]
    selected_robot_idx: int
    active_robot_name: str
    slots: List[CustomizeSlotItemModel]
    selected_slot_idx: int
    part_list: List[CustomizePartListItemModel]
    selected_part_list_idx: int
    detail: Optional[CustomizeDetailPanelModel] = None

    @property
    def slot_count(self) -> int:
        """スロット総数（レイアウト計算用の派生値）"""
        return len(self.slots)

    @property
    def part_list_count(self) -> int:
        """パーツ一覧の総数（レイアウト計算用の派生値）"""
        return len(self.part_list)