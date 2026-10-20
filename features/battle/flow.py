"""戦闘の進行制御・フェーズ遷移状態機械。

フェーズ全体の遷移フロー図:

  [ INITIAL_SETUP ] ──(準備完了)──> [ OPENING_LOG ] ──(確認)──> [ OPENING_POPUP ]
           │                              ▲                            │
           │ (開戦前入力)                   │ (初回のみ)                  │ (タイマー/スキップ)
           ▼                              │                            ▼
      [ INPUT ] <────────────────────────┴─────────────────────── [ IDLE ] <─────────┐
           │                                                        │                 │
           │ (コマンド決定)                                          │ (ATB手番発生)    │
           └────────────────────────────────────────────────────────┤                 │
                                                                    ▼                 │
     ┌─────────────────────────────────────────────────── [ 手番イベント判定 ]         │
     │                                                              │                 │
     │ (失敗 / スキップ)                                               │ (成功)          │
     ▼                                                              ▼                 │
  [ LOG_WAIT ] <───────────────────────────┐           [ TARGET_INDICATION ]          │
     │                                     │                        │ (タイマー)       │
     │                                     │                        ▼                 │
     │                                     │              [ ATTACK_DECLARATION ]      │
     │                                     │                        │                 │
     │                                     │ (LOG_ONLY)             ├─(CUTIN)──> [ CUTIN ]
     │                                     └────────────────────────┤               │
     │                                                              │               ▼
     │                                                              └──────> [ CUTIN_RESULT ]
     │ (確認)                                                                       │ (確認/貫通)
     ▼                                                                              │
  [ 行動完了 / 勝敗判定 ] <──────────────────────────────────────────────────────────┘
     ├─(決着)─> [ RESULT_LOG ] ──(確認)──> [ GAME_OVER ]
     └─(継続)─> [ IDLE ] へ復帰
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Union, TYPE_CHECKING

from domain.constants import CommandSlot, SkillPresentation
from .constants import BattlePhase, BattleTiming
from .entities.commands import ExecutionOutcome
from .events import ATBTurnEvent, PlayerInputRequiredEvent, ActionExecutedEvent

if TYPE_CHECKING:
    from .entities.robot import Robot
    from .manager import BattleManager


class AdvanceTrigger(Enum):
    """フェーズ前進の契機（トリガー区分）"""
    USER_CONFIRM = auto()
    TIMER = auto()
    ANIMATION_END = auto()


@dataclass(frozen=True)
class PhaseRule:
    """各フェーズの進行ルール定義"""
    advance_on: AdvanceTrigger
    next_phase: Optional[BattlePhase] = None
    duration: float = 0.0
    can_user_skip: bool = False


# フェーズ進行ルールテーブル（宣言的定義）
PHASE_RULES: Dict[BattlePhase, PhaseRule] = {
    BattlePhase.OPENING_LOG: PhaseRule(
        advance_on=AdvanceTrigger.USER_CONFIRM,
        next_phase=BattlePhase.OPENING_POPUP,
    ),
    BattlePhase.OPENING_POPUP: PhaseRule(
        advance_on=AdvanceTrigger.TIMER,
        next_phase=BattlePhase.IDLE,
        duration=BattleTiming.OPENING_POPUP,
        can_user_skip=True,
    ),
    BattlePhase.TARGET_INDICATION: PhaseRule(
        advance_on=AdvanceTrigger.TIMER,
        next_phase=BattlePhase.ATTACK_DECLARATION,
        duration=BattleTiming.TARGET_INDICATION,
        can_user_skip=False,
    ),
    BattlePhase.ATTACK_DECLARATION: PhaseRule(
        advance_on=AdvanceTrigger.USER_CONFIRM,
    ),
    BattlePhase.CUTIN: PhaseRule(
        advance_on=AdvanceTrigger.ANIMATION_END,
        next_phase=BattlePhase.CUTIN_RESULT,
        can_user_skip=True,
    ),
    BattlePhase.CUTIN_RESULT: PhaseRule(
        advance_on=AdvanceTrigger.USER_CONFIRM,
    ),
    BattlePhase.LOG_WAIT: PhaseRule(
        advance_on=AdvanceTrigger.USER_CONFIRM,
    ),
    BattlePhase.RESULT_LOG: PhaseRule(
        advance_on=AdvanceTrigger.USER_CONFIRM,
        next_phase=BattlePhase.GAME_OVER,
    ),
}

# 実行結果（ExecutionOutcome）から遷移先フェーズへの宣言的マッピングテーブル
OUTCOME_TO_PHASE: Dict[ExecutionOutcome, BattlePhase] = {
    ExecutionOutcome.OK: BattlePhase.TARGET_INDICATION,
    ExecutionOutcome.SKIPPED: BattlePhase.LOG_WAIT,
    ExecutionOutcome.PART_STOPPED: BattlePhase.LOG_WAIT,
    ExecutionOutcome.PART_UNUSABLE: BattlePhase.LOG_WAIT,
    ExecutionOutcome.TARGET_LOST: BattlePhase.LOG_WAIT,
    ExecutionOutcome.TRAP_DESTROYED: BattlePhase.LOG_WAIT,
    ExecutionOutcome.ACTION_UNIMPLEMENTED: BattlePhase.LOG_WAIT,
    ExecutionOutcome.RESERVED_PART_DESTROYED: BattlePhase.LOG_WAIT,
    ExecutionOutcome.NO_ACTION: BattlePhase.LOG_WAIT,
}


# ターンイベント種別に応じた遷移先フェーズ解決ディスパッチャ
_TURN_EVENT_RESOLVERS: Dict[type, Callable[[Any], Optional[BattlePhase]]] = {
    PlayerInputRequiredEvent: lambda _: BattlePhase.INPUT,
    ActionExecutedEvent: lambda e: OUTCOME_TO_PHASE.get(e.report.outcome, BattlePhase.LOG_WAIT),
}


@dataclass(frozen=True)
class PhaseChangeEvent:
    """フェーズ変更イベント"""
    old_phase: BattlePhase
    new_phase: BattlePhase


@dataclass(frozen=True)
class PierceStepEvent:
    """貫通演出の第2段階前進イベント"""
    target: 'Robot'


@dataclass(frozen=True)
class ActionCompletedEvent:
    """一連の行動演出・解決が完了したイベント"""
    pass


FlowEvent = Union[PhaseChangeEvent, PierceStepEvent, ActionCompletedEvent]


class BattleFlow:
    """戦闘の進行管理・フェーズ状態機械。フェーズの決定権を一元管理する。"""

    def __init__(self, manager: 'BattleManager'):
        self.manager = manager
        self.phase: BattlePhase = BattlePhase.INITIAL_SETUP
        self.timer: float = 0.0
        self.is_pierce_step: bool = False

    def can_advance_on(self, trigger: AdvanceTrigger) -> bool:
        rule = PHASE_RULES.get(self.phase)
        if not rule:
            return False
        if rule.advance_on == trigger:
            return True
        if trigger == AdvanceTrigger.USER_CONFIRM and rule.can_user_skip:
            return True
        return False

    def advance(self, trigger: AdvanceTrigger) -> List[FlowEvent]:
        if not self.can_advance_on(trigger):
            return []

        rule = PHASE_RULES.get(self.phase)

        if self.phase == BattlePhase.ATTACK_DECLARATION:
            return self._dispatch_by_presentation()
        elif self.phase == BattlePhase.CUTIN_RESULT:
            return self._advance_cutin_result()
        elif self.phase == BattlePhase.LOG_WAIT:
            return self._complete_action()

        if self.phase == BattlePhase.OPENING_POPUP:
            self.manager.ctx.is_opening_done = True
            self.manager.clear_log()
        elif self.phase == BattlePhase.CUTIN:
            self.manager.apply_execution_result()

        if rule and rule.next_phase:
            return self.change_phase(rule.next_phase)

        return []

    def _dispatch_by_presentation(self) -> List[FlowEvent]:
        actor = self.manager.current_actor
        part = actor.current_part if actor else None

        if not actor or not part or not part.is_implemented:
            if actor:
                self.manager.abort_current_actor()
            return self._complete_action()

        presentation = part.presentation
        if presentation == SkillPresentation.CUTIN:
            return self.change_phase(BattlePhase.CUTIN)
        elif presentation == SkillPresentation.LOG_ONLY:
            has_log = self.manager.apply_execution_result()
            if has_log:
                return self.change_phase(BattlePhase.LOG_WAIT)
            return self._complete_action()
        else:
            self.manager.apply_execution_result()
            return self._complete_action()

    def _advance_cutin_result(self) -> List[FlowEvent]:
        report = self.manager.ctx.current_report
        if report and report.has_pierce and not self.is_pierce_step and report.target:
            self.is_pierce_step = True
            self.manager.set_log(self.manager.logs.pierce())
            return [PierceStepEvent(target=report.target)]

        return self._complete_action()

    def _complete_action(self) -> List[FlowEvent]:
        events: List[FlowEvent] = [ActionCompletedEvent()]
        self.is_pierce_step = False
        self.manager.complete_execution()

        if self.manager.check_battle_end():
            events.extend(self.change_phase(BattlePhase.RESULT_LOG))
        else:
            self.manager.clear_log()
            events.extend(self.change_phase(BattlePhase.IDLE))

        return events

    def change_phase(self, new_phase: BattlePhase) -> List[FlowEvent]:
        old_phase = self.phase
        if old_phase == new_phase:
            return []

        self.phase = new_phase
        rule = PHASE_RULES.get(new_phase)
        self.timer = rule.duration if rule else 0.0

        if new_phase == BattlePhase.OPENING_LOG:
            self.manager.set_log(self.manager.logs.opening())
        elif new_phase == BattlePhase.ATTACK_DECLARATION:
            self.manager.setup_attack_declaration()
        elif new_phase == BattlePhase.RESULT_LOG:
            if self.manager.winner:
                self.manager.set_log(self.manager.logs.battle_end(self.manager.winner))

        return [PhaseChangeEvent(old_phase=old_phase, new_phase=new_phase)]

    def submit_player_command(self, slot: CommandSlot) -> List[FlowEvent]:
        if self.phase != BattlePhase.INPUT:
            return []

        accepted = self.manager.select_command_slot(slot)
        if not accepted:
            return []

        next_phase = BattlePhase.INITIAL_SETUP if not self.manager.is_opening_done else BattlePhase.IDLE
        return self.change_phase(next_phase)

    def update(self, dt: float) -> List[FlowEvent]:
        events: List[FlowEvent] = []

        rule = PHASE_RULES.get(self.phase)
        if rule and rule.advance_on == AdvanceTrigger.TIMER and self.timer > 0.0:
            self.timer = max(0.0, self.timer - dt)
            if self.timer <= 0.0:
                events.extend(self.advance(AdvanceTrigger.TIMER))
                return events

        if self.phase == BattlePhase.INITIAL_SETUP:
            ready_robot = self.manager.find_ready_player_robot()
            if ready_robot:
                self.manager.enter_input_phase(ready_robot)
                events.extend(self.change_phase(BattlePhase.INPUT))
            else:
                next_p = BattlePhase.OPENING_LOG if not self.manager.is_opening_done else BattlePhase.IDLE
                events.extend(self.change_phase(next_p))
            return events

        if self.phase == BattlePhase.IDLE:
            if self.manager.handle_charging_interrupts():
                events.extend(self.change_phase(BattlePhase.LOG_WAIT))
                return events

            turn_event: Optional[ATBTurnEvent] = self.manager.update_atb(dt)
            if turn_event is not None:
                next_phase = self._resolve_phase_from_turn_event(turn_event)
                if next_phase:
                    events.extend(self.change_phase(next_phase))

        return events

    def _resolve_phase_from_turn_event(self, turn_event: ATBTurnEvent) -> Optional[BattlePhase]:
        """テーブル駆動ディスパッチにより、イベントから遷移先フェーズをO(1)で決定する"""
        resolver = _TURN_EVENT_RESOLVERS.get(type(turn_event))
        return resolver(turn_event) if resolver else None