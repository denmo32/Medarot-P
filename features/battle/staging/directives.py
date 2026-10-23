"""戦闘シーケンスの指示（Directive）および待機条件（Await）の定義。"""
from dataclasses import dataclass
from typing import Any, List, Optional, TYPE_CHECKING
from domain.constants import COMMAND_MENU_PART_ORDER, PartType
from core.inputs import InputState
from features.battle.input.command_menu_navigation import resolve_command_menu_navigation

if TYPE_CHECKING:
    from features.battle.entities.commands import ExecutionReport
    from features.battle.entities.part import Part
    from features.battle.entities.robot import Robot
    from features.battle.events import ATBTurnEvent
    from features.battle.staging.director import BattleDirector


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
# 待機指示 (Await Directives)
# ==============================================================================

class Await(Directive):
    """条件が満たされるまで進行を停止する待機オブジェクトの基底クラス"""

    def tick(self, dt: float, director: 'BattleDirector'):
        pass

    def handle_input(self, input_state: InputState, director: 'BattleDirector') -> bool:
        return False

    def is_done(self, director: 'BattleDirector') -> bool:
        return True

    def take_result(self) -> Any:
        return None


@dataclass
class AwaitTime(Await):
    remaining: float
    can_skip: bool = False

    def tick(self, dt: float, director: 'BattleDirector'):
        self.remaining = max(0.0, self.remaining - dt)

    def handle_input(self, input_state: InputState, director: 'BattleDirector') -> bool:
        if self.can_skip and (input_state.btn_ok or input_state.mouse_clicked):
            self.remaining = 0.0
            return True
        return False

    def is_done(self, director: 'BattleDirector') -> bool:
        return self.remaining <= 0.0


@dataclass
class AwaitUserConfirm(Await):
    _confirmed: bool = False

    def handle_input(self, input_state: InputState, director: 'BattleDirector') -> bool:
        # Facade 経由で判定
        if (input_state.btn_ok or input_state.mouse_clicked) and not director.is_hp_animating():
            self._confirmed = True
            return True
        return False

    def is_done(self, director: 'BattleDirector') -> bool:
        return self._confirmed


@dataclass
class AwaitHpAnimation(Await):
    def is_done(self, director: 'BattleDirector') -> bool:
        # Facade 経由で判定
        return not director.is_hp_animating()


@dataclass
class AwaitCutin(Await):
    _finished: bool = False

    def tick(self, dt: float, director: 'BattleDirector'):
        director.update_cutin(dt)
        if director.is_cutin_finished():
            self._finished = True

    def handle_input(self, input_state: InputState, director: 'BattleDirector') -> bool:
        if input_state.btn_ok or input_state.mouse_clicked:
            director.advance_cutin()
            self._finished = True
            return True
        return False

    def is_done(self, director: 'BattleDirector') -> bool:
        return self._finished


@dataclass
class AwaitPlayerInput(Await):
    actor: 'Robot'
    preview_targets: dict
    selected_index: int = 0
    _selected_part: Optional[PartType] = None
    _is_submitted: bool = False

    def _get_selectable_mask(self) -> List[bool]:
        mask = []
        for pt in COMMAND_MENU_PART_ORDER:
            if pt is None:
                mask.append(True)  # スキップは常に可能
                continue
            part = self.actor.get_part(pt)
            can_exec = part.can_execute if part else False
            if can_exec and part.locks_target and not self.preview_targets.get(pt):
                can_exec = False
            mask.append(can_exec)
        return mask

    def handle_input(self, input_state: InputState, director: 'BattleDirector') -> bool:
        """キーボード/ゲームパッド入力による移動と決定"""
        selectable_mask = self._get_selectable_mask()
        self.selected_index = resolve_command_menu_navigation(
            self.selected_index, input_state, selectable_mask
        )
        if input_state.btn_ok and selectable_mask[self.selected_index]:
            self.submit(COMMAND_MENU_PART_ORDER[self.selected_index])
            return True
        return False

    def try_mouse_select(self, new_index: int, confirmed: bool) -> bool:
        """Scene から渡されたマウスヒットテスト結果をカプセル化して確定"""
        selectable_mask = self._get_selectable_mask()
        if 0 <= new_index < len(selectable_mask) and selectable_mask[new_index]:
            self.selected_index = new_index
        if confirmed and selectable_mask[self.selected_index]:
            self.submit(COMMAND_MENU_PART_ORDER[self.selected_index])
            return True
        return False

    def submit(self, part_type: Optional[PartType]):
        """コマンドを決定する（None はスキップ）"""
        self._selected_part = part_type
        self._is_submitted = True

    def is_done(self, director: 'BattleDirector') -> bool:
        return self._is_submitted

    def take_result(self) -> Optional[PartType]:
        return self._selected_part


@dataclass
class AwaitNextTurn(Await):
    _event: Optional['ATBTurnEvent'] = None

    def tick(self, dt: float, director: 'BattleDirector'):
        # Facade 経由で進行
        turn = director.update_atb(dt)
        if turn is not None:
            self._event = turn

    def is_done(self, director: 'BattleDirector') -> bool:
        return self._event is not None

    def take_result(self) -> Optional['ATBTurnEvent']:
        return self._event