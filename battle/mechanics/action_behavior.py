"""アクション種別ごとの実行振る舞いロジック"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from domain.constants import ActionType
from battle.constants import BattlePhase
from battle.mechanics.action import ActionMechanics, GaugeResetData
from battle.mechanics.log import LogBuilder
from components.battle_component import StatusEffect

if TYPE_CHECKING:
    from components.battle_component import DamageEventComponent

@dataclass(frozen=True)
class DamageResult:
    """攻撃によって発生するダメージ情報の指示書"""
    attacker_id: int
    attacker_part: str
    damage: int
    target_part: str
    is_critical: bool = False
    added_effects: List[StatusEffect] = field(default_factory=list)

    def to_component(self) -> 'DamageEventComponent':
        """
        DamageEventComponent を生成する。

        Returns:
            DamageEventComponent インスタンス
        """
        from components.battle_component import DamageEventComponent
        return DamageEventComponent(
            attacker_id=self.attacker_id,
            attacker_part=self.attacker_part,
            damage=self.damage,
            target_part=self.target_part,
            is_critical=self.is_critical,
            added_effects=self.added_effects
        )

@dataclass
class ResolutionResult:
    """アクション解決の結果を表すデータオブジェクト（副作用の指示書）"""
    next_phase: str
    phase_timer: float = 0.0
    damage_result: Optional[DamageResult] = None
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
    calculation_result: Optional['CombatResult']


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
        # TargetResolver によって解決済みのターゲットを使用
        if not params.is_actor_part_alive:
            return None, None
        return params.resolved_target_id, params.resolved_target_part

    def get_initial_phase(self) -> str:
        return BattlePhase.TARGET_INDICATION

    def resolve(self, context: ResolveContext) -> ResolutionResult:
        # 実行直前の生存チェック
        if not context.is_actor_part_alive:
            return ResolutionResult(
                next_phase=BattlePhase.LOG_WAIT,
                logs=[LogBuilder.get_part_broken_attack(context.attacker_name)],
                gauge_reset=ActionMechanics.get_cooldown_reset_data(0.0)
            )

        damage_result = None
        if context.calculation_result and context.calculation_result.is_hit:
            res = context.calculation_result
            damage_result = DamageResult(
                attacker_id=0,  # event から取得されるため、ここではダミー
                attacker_part="",  # event から取得されるため、ここではダミー
                damage=res.damage,
                target_part=res.hit_part,
                is_critical=res.is_critical,
                added_effects=res.added_effects
            )

        return ResolutionResult(
            next_phase=BattlePhase.CUTIN_RESULT,
            damage_result=damage_result,
            gauge_reset=ActionMechanics.get_cooldown_reset_data(100.0)  # 実行完了なので 100% から放熱
        )

class SkipAction(ActionBehavior):
    def initiate(self, params: InitiateParams) -> Tuple[Optional[int], Optional[str]]:
        # スキップは常に成功（ターゲットは自分自身）
        return 0, None

    def get_initial_phase(self) -> str:
        return BattlePhase.EXECUTING

    def resolve(self, context: ResolveContext) -> ResolutionResult:
        return ResolutionResult(
            next_phase=BattlePhase.LOG_WAIT,
            logs=[LogBuilder.get_skip_action(context.attacker_name)],
            gauge_reset=ActionMechanics.get_cooldown_reset_data(0.0)
        )

class ActionBehaviorRegistry:
    """ActionBehavior のカタログ"""
    _behaviors = {
        ActionType.ATTACK: AttackAction(),
        ActionType.SKIP: SkipAction()
    }

    @classmethod
    def get(cls, action_type: str) -> ActionBehavior:
        return cls._behaviors.get(action_type, SkipAction())
