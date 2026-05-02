"""アクション種別ごとの実行振る舞い・状態遷移ロジック"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from domain.constants import ActionType, GaugeStatus
from battle.constants import BattlePhase
from domain.models import CombatResult
from domain.log_logic import get_part_broken_attack, get_skip_action

@dataclass(frozen=True)
class InterruptionResult:
    """中断判定の結果"""
    is_interrupted: bool
    message: Optional[str] = None

@dataclass(frozen=True)
class GaugeResetData:
    """ゲージをリセットする際の計算済みパラメータ"""
    status: str
    progress: float
    clear_selection: bool = True

def check_action_interruption(
    status: str,
    selected_action: str,
    selected_part: Optional[str],
    is_actor_part_alive: bool,
    target_data: Optional[Tuple[int, str]],
    is_target_part_alive: bool,
    actor_name: str
) -> InterruptionResult:
    """行動の継続妥当性を検証し、必要なら中断メッセージを返す。"""
    if status not in (GaugeStatus.CHARGING, GaugeStatus.ACTION_CHOICE):
        return InterruptionResult(is_interrupted=False)

    if selected_action == ActionType.ATTACK and selected_part and not is_actor_part_alive:
        return InterruptionResult(is_interrupted=True, message=f"{actor_name}の予約パーツは破壊された！")

    if target_data and not is_target_part_alive:
        return InterruptionResult(is_interrupted=True, message=f"{actor_name}はターゲットロストした！")

    return InterruptionResult(is_interrupted=False)

@dataclass
class ResolutionResult:
    """アクション解決の結果を表すデータオブジェクト（副作用の指示書）"""
    next_phase: str
    phase_timer: float = 0.0
    calculation_result: Optional[CombatResult] = None
    logs: List[str] = field(default_factory=list)
    gauge_reset: Optional[GaugeResetData] = None
    should_remove_from_queue: bool = True


@dataclass(frozen=True)
class InitiateParams:
    """ActionBehavior.initiate に渡すパラメータ"""
    selected_action: str
    selected_part: Optional[str]
    is_actor_part_alive: bool
    attack_trait: str
    # TargetResolver によって解決されたターゲット
    resolved_target_id: Optional[int]
    resolved_target_part: Optional[str]


@dataclass(frozen=True)
class ResolveContext:
    """ActionBehavior.resolve に渡すコンテキスト"""
    attacker_name: str
    is_actor_part_alive: bool
    calculation_result: Optional[CombatResult]


class ActionBehavior(ABC):
    """アクション（攻撃、スキップ等）の具体的な振る舞いを定義する基底クラス"""

    @abstractmethod
    def initiate(self, params: InitiateParams) -> Tuple[Optional[int], Optional[str]]:
        """ActionEvent 生成のためのターゲット解決。失敗（中断）時は (None, None) を返す"""
        pass

    @abstractmethod
    def get_initial_phase(self) -> str:
        """アクション開始時の最初の遷移フェーズ"""
        pass

    @abstractmethod
    def resolve(self, context: ResolveContext) -> ResolutionResult:
        """アクション実行の結果（演出終了後）を計算して返す"""
        pass

class AttackAction(ActionBehavior):
    def initiate(self, params: InitiateParams) -> Tuple[Optional[int], Optional[str]]:
        if not params.is_actor_part_alive:
            return None, None
        return params.resolved_target_id, params.resolved_target_part

    def get_initial_phase(self) -> str:
        return BattlePhase.TARGET_INDICATION

    def resolve(self, context: ResolveContext) -> ResolutionResult:
        if not context.is_actor_part_alive:
            return ResolutionResult(
                next_phase=BattlePhase.LOG_WAIT,
                logs=[get_part_broken_attack(context.attacker_name)],
                gauge_reset=get_cooldown_reset_data(0.0)
            )

        return ResolutionResult(
            next_phase=BattlePhase.CUTIN_RESULT,
            calculation_result=context.calculation_result,
            gauge_reset=get_cooldown_reset_data(100.0)
        )

class SkipAction(ActionBehavior):
    def initiate(self, params: InitiateParams) -> Tuple[Optional[int], Optional[str]]:
        return 0, None

    def get_initial_phase(self) -> str:
        return BattlePhase.EXECUTING

    def resolve(self, context: ResolveContext) -> ResolutionResult:
        return ResolutionResult(
            next_phase=BattlePhase.LOG_WAIT,
            logs=[get_skip_action(context.attacker_name)],
            gauge_reset=get_cooldown_reset_data(0.0)
        )

_behaviors = {
    ActionType.ATTACK: AttackAction(),
    ActionType.SKIP: SkipAction()
}

def get_action_behavior(action_type: str) -> ActionBehavior:
    """指定されたアクション種別の振る舞いを取得する。"""
    return _behaviors.get(action_type, SkipAction())


# --- Action Mechanics (from action.py) ---

def get_cooldown_reset_data(current_progress: float, use_penalty: bool = True) -> GaugeResetData:
    """放熱状態へリセットするためのデータを計算する。"""
    if use_penalty:
        new_progress = max(0.0, 100.0 - current_progress)
    else:
        new_progress = 0.0

    return GaugeResetData(
        status=GaugeStatus.COOLDOWN,
        progress=new_progress,
        clear_selection=False
    )

def get_choice_reset_data() -> GaugeResetData:
    """行動選択状態へリセットするためのデータを計算する。"""
    return GaugeResetData(
        status=GaugeStatus.ACTION_CHOICE,
        progress=0.0,
        clear_selection=True
    )
