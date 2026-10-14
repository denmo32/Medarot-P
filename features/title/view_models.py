"""タイトル画面の表示専用データ構造（View Model）。"""
from dataclasses import dataclass
from typing import List
from domain.constants import SceneId


@dataclass(frozen=True)
class TitleButtonModel:
    text: str
    target: SceneId
    cx: float
    cy: float
    w_ratio: float
    h_ratio: float
    is_selected: bool


@dataclass(frozen=True)
class TitleViewModel:
    buttons: List[TitleButtonModel]
    selected_index: int