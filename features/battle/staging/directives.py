"""戦闘シーケンスの指示（Directive）および待機条件（Await）の定義。"""
from dataclasses import dataclass
from typing import Any, List, Optional, TYPE_CHECKING
from domain.constants import PartType
from core.inputs import InputState

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
    target: 'Robot'
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
        if (input_state.btn_ok or input_state.mouse_clicked) and not director.visual.is_hp_animating():
            self._confirmed = True
            return True
        return False

    def is_done(self, director: 'BattleDirector') -> bool:
        return self._confirmed


@dataclass
class AwaitHpAnimation(Await):
    def is_done(self, director: 'BattleDirector') -> bool:
        return not director.visual.is_hp_animating()


@dataclass
class AwaitCutin(Await):
    _finished: bool = False

    def tick(self, dt: float, director: 'BattleDirector'):
        director.visual.update_cutin(dt)
        if not director.visual.cutin_director or director.visual.cutin_director.is_animation_finished:
            self._finished = True

    def handle_input(self, input_state: InputState, director: 'BattleDirector') -> bool:
        if input_state.btn_ok or input_state.mouse_clicked:
            director.visual.advance_cutin()
            self._finished = True
            return True
        return False

    def is_done(self, director: 'BattleDirector') -> bool:
        return self._finished


@dataclass
class AwaitPlayerInput(Await):
    actor: 'Robot'
    preview_targets: dict
    _selected_part: Optional[PartType] = None
    _is_submitted: bool = False

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
        turn = director.manager.update_atb(dt)
        if turn is not None:
            self._event = turn

    def is_done(self, director: 'BattleDirector') -> bool:
        return self._event is not None

    def take_result(self) -> Optional['ATBTurnEvent']:
        return self._event