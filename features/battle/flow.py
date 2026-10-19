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
    """フェーズ前進の契機（トリガー区分）。

    発火主体:
    - USER_CONFIRM: プレイヤーの明示的操作（決定キー押下 / マウスクリック） -> BattleScene (Input) が発火
    - TIMER: 設定時間（duration）の満了 -> BattleFlow.update() が自己発火
    - ANIMATION_END: 演出（カットイン等）の物理的完了 -> BattleScene (VisualCoordinator) が通知
    """
    USER_CONFIRM = auto()
    TIMER = auto()
    ANIMATION_END = auto()


@dataclass(frozen=True)
class PhaseRule:
    """各フェーズの進行ルール定義"""
    advance_on: AdvanceTrigger
    next_phase: Optional[BattlePhase] = None
    duration: float = 0.0
    can_user_skip: bool = False  # タイマー/演出中でもユーザー操作でスキップ可能か


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
        # 技の presentation (CUTIN / LOG_ONLY / NONE) に応じて動的に分岐
    ),
    BattlePhase.CUTIN: PhaseRule(
        advance_on=AdvanceTrigger.ANIMATION_END,
        next_phase=BattlePhase.CUTIN_RESULT,
        can_user_skip=True,
    ),
    BattlePhase.CUTIN_RESULT: PhaseRule(
        advance_on=AdvanceTrigger.USER_CONFIRM,
        # 貫通ステップ継続、または行動完了へ動的に分岐
    ),
    BattlePhase.LOG_WAIT: PhaseRule(
        advance_on=AdvanceTrigger.USER_CONFIRM,
        # 行動完了（通常は IDLE、勝敗決着時は RESULT_LOG）へ動的に遷移
    ),
    BattlePhase.RESULT_LOG: PhaseRule(
        advance_on=AdvanceTrigger.USER_CONFIRM,
        next_phase=BattlePhase.GAME_OVER,
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
        """トリガーを受け取り、条件に合致すればフェーズを前進させる。"""
        if not self.can_advance_on(trigger):
            return []

        rule = PHASE_RULES.get(self.phase)

        # 動的分岐または固有の完了処理を持つフェーズのハンドリング
        if self.phase == BattlePhase.ATTACK_DECLARATION:
            return self._dispatch_by_presentation()
        elif self.phase == BattlePhase.CUTIN_RESULT:
            return self._advance_cutin_result()
        elif self.phase == BattlePhase.LOG_WAIT:
            return self._complete_action()

        # フェーズ退出時の固有副作用（フック）
        if self.phase == BattlePhase.OPENING_POPUP:
            self.manager.ctx.is_opening_done = True
            self.manager.clear_log()
        elif self.phase == BattlePhase.CUTIN:
            # カットイン演出完了時にダメージ効果を世界状態へ確定反映する
            self.manager.apply_execution_result()

        # テーブルで宣言された next_phase に従って遷移
        if rule and rule.next_phase:
            return self.change_phase(rule.next_phase)

        return []

    def _dispatch_by_presentation(self) -> List[FlowEvent]:
        """行動宣言確認後、技の演出形式（Presentation）に応じたフェーズへ分岐する。"""
        actor = self.manager.current_actor
        part = actor.current_part if actor else None

        if not actor or not part or not part.is_implemented:
            if actor:
                self.manager.abort_current_actor()
            return self._complete_action()

        presentation = part.presentation
        if presentation == SkillPresentation.CUTIN:
            # カットイン演出へ。効果適用は CUTIN 終了時（CUTIN_RESULT 遷移時）に行われる
            return self.change_phase(BattlePhase.CUTIN)
        elif presentation == SkillPresentation.LOG_ONLY:
            # カットインなし。即時効果適用し、ログ表示フェーズへ
            has_log = self.manager.apply_execution_result()
            if has_log:
                return self.change_phase(BattlePhase.LOG_WAIT)
            return self._complete_action()
        else:
            self.manager.apply_execution_result()
            return self._complete_action()

    def _advance_cutin_result(self) -> List[FlowEvent]:
        """カットイン結果確認後、貫通演出ステップに進むか行動完了とするかを判定する。"""
        report = self.manager.ctx.current_report
        if report and report.has_pierce and not self.is_pierce_step and report.target:
            self.is_pierce_step = True
            self.manager.set_log(self.manager.logs.pierce())
            return [PierceStepEvent(target=report.target)]

        return self._complete_action()

    def _complete_action(self) -> List[FlowEvent]:
        """一連の行動演出・解決を終了し、勝敗判定を行って次のフェーズ（RESULT_LOG または IDLE）へ進む。"""
        events: List[FlowEvent] = [ActionCompletedEvent()]
        self.is_pierce_step = False
        self.manager.complete_execution()

        if self.manager.check_battle_end():
            # リーダー撃破により決着：勝敗ログ表示フェーズへ遷移
            events.extend(self.change_phase(BattlePhase.RESULT_LOG))
        else:
            self.manager.clear_log()
            events.extend(self.change_phase(BattlePhase.IDLE))

        return events

    def change_phase(self, new_phase: BattlePhase) -> List[FlowEvent]:
        """フェーズを変更し、対応する初期化処理を行って PhaseChangeEvent を発行する。"""
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
        """プレイヤーのコマンド入力を処理し、状態機械を適切なフェーズへ前進させる。"""
        if self.phase != BattlePhase.INPUT:
            return []

        accepted = self.manager.select_command_slot(slot)
        if not accepted:
            return []

        # 開戦前なら待機中の自軍機体（2機目・3機目）の入力確認のため INITIAL_SETUP へ、開戦後なら IDLE へ
        next_phase = BattlePhase.INITIAL_SETUP if not self.manager.is_opening_done else BattlePhase.IDLE
        return self.change_phase(next_phase)

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

        # 2. 初期セットアップ進行（開戦前の機体コマンド入力・開始演出への移行）
        if self.phase == BattlePhase.INITIAL_SETUP:
            ready_robot = self.manager.find_ready_player_robot()
            if ready_robot:
                self.manager.enter_input_phase(ready_robot)
                events.extend(self.change_phase(BattlePhase.INPUT))
            else:
                next_p = BattlePhase.OPENING_LOG if not self.manager.is_opening_done else BattlePhase.IDLE
                events.extend(self.change_phase(next_p))
            return events

        # 3. IDLE 進行（シミュレーション）
        if self.phase == BattlePhase.IDLE:
            if self.manager.handle_charging_interrupts():
                events.extend(self.change_phase(BattlePhase.LOG_WAIT))
                return events

            next_phase = self.manager.update_atb(dt)
            if next_phase:
                events.extend(self.change_phase(next_phase))

        return events