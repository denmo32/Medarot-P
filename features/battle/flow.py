"""戦闘の進行制御・フェーズ遷移状態機械（離散イベント駆動＋連続時間タイマー）。

シミュレーション（BattleManager）や演出（VisualCoordinator）から独立し、
「誰が・何のトリガーで・どのフェーズへ進むか」の遷移規則のみを一元管理します。
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Union, TYPE_CHECKING

from domain.constants import CommandSlot, SkillPresentation
from .constants import BattlePhase, BattleTiming

if TYPE_CHECKING:
    from .entities.robot import Robot
    from .manager import BattleManager


class AdvanceTrigger(Enum):
    """フェーズ前進の契機（トリガー区分）"""
    USER_CONFIRM = auto()    # ユーザー決定・マウスクリック
    TIMER = auto()           # タイマー満了
    ANIMATION_END = auto()   # 演出（カットインなど）の物理的終了


@dataclass(frozen=True)
class PhaseRule:
    """各フェーズの進行ルール定義"""
    advance_on: AdvanceTrigger
    next_phase: Optional[BattlePhase] = None
    duration: float = 0.0
    can_user_skip: bool = False  # タイマー/アニメ中でもユーザー確認で前進可能か


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
    """戦闘の進行管理・フェーズ状態機械。"""

    def __init__(self, manager: 'BattleManager'):
        self.manager = manager
        self.phase: BattlePhase = BattlePhase.INITIAL_SETUP
        self.timer: float = 0.0
        self.is_pierce_step: bool = False

    def can_advance_on(self, trigger: AdvanceTrigger) -> bool:
        """指定されたトリガーで現在のフェーズが進めるかを判定する"""
        rule = PHASE_RULES.get(self.phase)
        if not rule:
            return False
        if rule.advance_on == trigger:
            return True
        if trigger == AdvanceTrigger.USER_CONFIRM and rule.can_user_skip:
            return True
        return False

    def advance(self, trigger: AdvanceTrigger) -> List[FlowEvent]:
        """トリガーを受け取り、条件に合致すればフェーズを前進させる"""
        if not self.can_advance_on(trigger):
            return []

        events: List[FlowEvent] = []

        if self.phase == BattlePhase.OPENING_LOG:
            events.extend(self.change_phase(BattlePhase.OPENING_POPUP))

        elif self.phase == BattlePhase.OPENING_POPUP:
            self.manager.ctx.is_opening_done = True
            self.manager.ctx.clear_log()
            events.extend(self.change_phase(BattlePhase.IDLE))

        elif self.phase == BattlePhase.TARGET_INDICATION:
            events.extend(self.change_phase(BattlePhase.ATTACK_DECLARATION))

        elif self.phase == BattlePhase.ATTACK_DECLARATION:
            events.extend(self._advance_attack_declaration())

        elif self.phase == BattlePhase.CUTIN:
            self.manager.apply_execution_result()
            events.extend(self.change_phase(BattlePhase.CUTIN_RESULT))

        elif self.phase == BattlePhase.CUTIN_RESULT:
            events.extend(self._advance_cutin_result())

        elif self.phase == BattlePhase.LOG_WAIT:
            events.extend(self._complete_action())

        return events

    def _advance_attack_declaration(self) -> List[FlowEvent]:
        actor = self.manager.current_actor
        part = actor.current_part if actor else None

        if not actor or not part or not part.is_implemented:
            if actor:
                actor.enter_cooldown(interrupted=False)
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
            self.manager.ctx.set_log(["貫通ダメージ！"])
            return [PierceStepEvent(target=report.target)]

        return self._complete_action()

    def _complete_action(self) -> List[FlowEvent]:
        events: List[FlowEvent] = [ActionCompletedEvent()]
        self.is_pierce_step = False
        self.manager.complete_execution()

        if self.manager.check_battle_end():
            if not self.manager.ctx.result_announced:
                self.manager.ctx.result_announced = True
                self.manager.ctx.set_log(self.manager.logs.battle_end(self.manager.ctx.winner))
                events.extend(self.change_phase(BattlePhase.LOG_WAIT))
            else:
                events.extend(self.change_phase(BattlePhase.GAME_OVER))
        else:
            self.manager.ctx.clear_log()
            events.extend(self.change_phase(BattlePhase.IDLE))

        return events

    def change_phase(self, new_phase: BattlePhase) -> List[FlowEvent]:
        old_phase = self.phase
        if old_phase == new_phase:
            return []

        self.phase = new_phase
        self.manager.ctx.phase = new_phase  # コンテキストと描画モデルの同期
        rule = PHASE_RULES.get(new_phase)
        self.timer = rule.duration if rule else 0.0

        if new_phase == BattlePhase.OPENING_LOG:
            self.manager.ctx.set_log(self.manager.logs.opening())
        elif new_phase == BattlePhase.ATTACK_DECLARATION:
            self.manager.setup_attack_declaration()

        return [PhaseChangeEvent(old_phase=old_phase, new_phase=new_phase)]

    def submit_player_command(self, slot: CommandSlot) -> List[FlowEvent]:
        next_phase = self.manager.select_command_slot(slot)
        if next_phase:
            return self.change_phase(next_phase)
        return []

    def update(self, dt: float) -> List[FlowEvent]:
        """毎フレームのタイマー更新およびシミュレーション進行"""
        events: List[FlowEvent] = []

        # 1. 時間駆動フェーズのタイマー進行
        rule = PHASE_RULES.get(self.phase)
        if rule and rule.advance_on == AdvanceTrigger.TIMER and self.timer > 0.0:
            self.timer = max(0.0, self.timer - dt)
            if self.timer <= 0.0:
                events.extend(self.advance(AdvanceTrigger.TIMER))
                return events

        # 2. 初期セットアップ進行
        if self.phase == BattlePhase.INITIAL_SETUP:
            ready_robot = self.manager.find_ready_player_robot()
            if ready_robot:
                self.manager.enter_input_phase(ready_robot)
                events.extend(self.change_phase(BattlePhase.INPUT))
            else:
                next_p = BattlePhase.OPENING_LOG if not self.manager.ctx.is_opening_done else BattlePhase.IDLE
                events.extend(self.change_phase(next_p))
            return events

        # 3. IDLE 進行（シミュレーション）
        if self.phase == BattlePhase.IDLE:
            if self.manager.check_battle_end():
                events.extend(self._complete_action())
                return events

            if self.manager.handle_charging_interrupts():
                events.extend(self.change_phase(BattlePhase.LOG_WAIT))
                return events

            next_phase = self.manager.update_atb(dt)
            if next_phase:
                events.extend(self.change_phase(next_phase))

        return events