"""アクション種別ごとの実行振る舞いロジック"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from domain.constants import ActionType
from battle.constants import BattlePhase
from battle.mechanics.action import ActionMechanics
from battle.mechanics.log import LogBuilder
from components.battle_component import DamageEventComponent

@dataclass
class ResolutionResult:
    """アクション解決の結果を表すデータオブジェクト（副作用の指示書）"""
    next_phase: str
    phase_timer: float = 0.0
    damage_event: Optional[DamageEventComponent] = None
    logs: List[str] = field(default_factory=list)
    should_reset_gauge: bool = True

class ActionBehavior(ABC):
    """アクション（攻撃、スキップ等）の具体的な振る舞いを定義する基底クラス"""

    @abstractmethod
    def initiate(self, world, actor_eid: int, actor_comps, gauge) -> Tuple[Optional[int], Optional[str]]:
        """ActionEvent生成のためのターゲット解決。失敗（中断）時は (None, None) を返す"""
        pass

    @abstractmethod
    def get_initial_phase(self) -> str:
        """アクション開始時の最初の遷移フェーズ"""
        pass

    @abstractmethod
    def resolve(self, world, event, context) -> ResolutionResult:
        """アクション実行の結果（演出終了後）を計算して返す"""
        pass

class AttackAction(ActionBehavior):
    def initiate(self, world, actor_eid: int, actor_comps, gauge) -> Tuple[Optional[int], Optional[str]]:
        return ActionMechanics.resolve_action_target(world, actor_eid, actor_comps, gauge)

    def get_initial_phase(self) -> str:
        return BattlePhase.TARGET_INDICATION

    def resolve(self, world, event, context) -> ResolutionResult:
        attacker_comps = world.try_get_entity(event.attacker_id)
        attacker_name = attacker_comps['medal'].nickname
        part_id = attacker_comps['partlist'].parts.get(event.part_type)
        part_comps = world.try_get_entity(part_id)
        
        # 実行直前の生存チェック
        if not part_comps or part_comps['health'].hp <= 0:
            return ResolutionResult(
                next_phase=BattlePhase.LOG_WAIT,
                logs=[LogBuilder.get_part_broken_attack(attacker_name)]
            )

        res = event.calculation_result
        damage_event = None
        if res and res.is_hit:
            damage_event = DamageEventComponent(
                attacker_id=event.attacker_id,
                attacker_part=event.part_type,
                damage=res.damage,
                target_part=res.hit_part,
                is_critical=res.is_critical,
                added_effects=res.added_effects
            )
        
        return ResolutionResult(
            next_phase=BattlePhase.CUTIN_RESULT,
            damage_event=damage_event
        )

class SkipAction(ActionBehavior):
    def initiate(self, world, actor_eid: int, actor_comps, gauge) -> Tuple[Optional[int], Optional[str]]:
        return actor_eid, None

    def get_initial_phase(self) -> str:
        return BattlePhase.EXECUTING

    def resolve(self, world, event, context) -> ResolutionResult:
        attacker_comps = world.try_get_entity(event.attacker_id)
        name = attacker_comps['medal'].nickname
        return ResolutionResult(
            next_phase=BattlePhase.LOG_WAIT,
            logs=[LogBuilder.get_skip_action(name)]
        )

class ActionBehaviorRegistry:
    """ActionBehaviorのカタログ"""
    _behaviors = {
        ActionType.ATTACK: AttackAction(),
        ActionType.SKIP: SkipAction()
    }
    
    @classmethod
    def get(cls, action_type: str) -> ActionBehavior:
        return cls._behaviors.get(action_type, SkipAction())