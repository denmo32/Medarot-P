# features/battle/staging/directives.py
"""戦闘シーケンスの指示（Directive）および待機条件（Await）の定義。"""
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple, TYPE_CHECKING
from domain.constants import COMMAND_MENU_PART_ORDER, PartType
from core.inputs import InputState
from features.battle.input.command_menu_navigation import resolve_command_menu_navigation

if TYPE_CHECKING:
    from features.battle.simulation.entities.commands import ExecutionReport
    from features.battle.simulation.entities.part import Part
    from features.battle.simulation.entities.robot import Robot


# ==============================================================================
# 即時指示 (Action Directives)
# ==============================================================================

class Directive:
    """戦闘シーケンス内で発行される即時指示の基底クラス"""
    pass


@dataclass(frozen=True)
class ShowLog(Directive):
    messages: List[str]


@dataclass(frozen=True)
class StartRadar(Directive):
    attacker_index: int
    target_index: int


@dataclass(frozen=True)
class ClearRadar(Directive):
    pass


@dataclass(frozen=True)
class StartCutin(Directive):
    actor: 'Robot'
    target: 'Robot'
    part: Optional['Part']
    report: 'ExecutionReport'


@dataclass(frozen=True)
class StageDamage(Directive):
    report: 'ExecutionReport'


@dataclass(frozen=True)
class AdvanceCutinPierce(Directive):
    report: 'ExecutionReport'


@dataclass(frozen=True)
class ClearCutin(Directive):
    pass


@dataclass(frozen=True)
class SetOpeningPopupVisible(Directive):
    visible: bool


# ==============================================================================
# 待機指示 (Await Directives) - 純粋データトークン
# ==============================================================================

class Await(Directive):
    """進行停止・待機条件を表すトークンの基底クラス"""
    pass


@dataclass
class AwaitTime(Await):
    remaining: float
    can_skip: bool = False


@dataclass(frozen=True)
class AwaitUserConfirm(Await):
    pass


@dataclass(frozen=True)
class AwaitHpAnimation(Await):
    pass


@dataclass(frozen=True)
class AwaitCutin(Await):
    pass


@dataclass(frozen=True)
class AwaitNextTurn(Await):
    pass


@dataclass
class AwaitPlayerInput(Await):
    actor: 'Robot'
    preview_targets: dict
    selectable_mask: Tuple[bool, ...]
    selected_index: int = 0
    _selected_part: Optional[PartType] = None
    _is_submitted: bool = False

    def handle_input(self, input_state: InputState) -> bool:
        """キーボード/ゲームパッド入力による移動と決定"""
        self.selected_index = resolve_command_menu_navigation(
            self.selected_index, input_state, self.selectable_mask
        )
        if input_state.btn_ok and self.selectable_mask[self.selected_index]:
            self.submit(COMMAND_MENU_PART_ORDER[self.selected_index])
            return True
        return False

    def try_mouse_select(self, new_index: int, confirmed: bool) -> bool:
        """マウスヒットテスト結果に基づく選択・決定"""
        if 0 <= new_index < len(self.selectable_mask) and self.selectable_mask[new_index]:
            self.selected_index = new_index
        if confirmed and self.selectable_mask[self.selected_index]:
            self.submit(COMMAND_MENU_PART_ORDER[self.selected_index])
            return True
        return False

    def submit(self, part_type: Optional[PartType]):
        """コマンドを決定する（None はスキップ）"""
        self._selected_part = part_type
        self._is_submitted = True

    @property
    def is_done(self) -> bool:
        return self._is_submitted

    def take_result(self) -> Optional[PartType]:
        return self._selected_part