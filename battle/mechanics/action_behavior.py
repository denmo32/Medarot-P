"""アクション種別ごとの実行振る舞いロジック"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from domain.constants import ActionType, GaugeStatus
from battle.constants import BattlePhase, BattleTiming
from battle.mechanics.action import ActionMechanics
from battle.mechanics.combat import CombatMechanics
from battle.mechanics.log import LogBuilder
from battle.mechanics.flow import transition_to_phase
from components.action_event_component import ActionEventComponent
from components.battle_component import DamageEventComponent

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
    def resolve(self, world, event, context, flow):
        """アクション実行（演出終了後）の副作用適用"""
        pass

class AttackAction(ActionBehavior):
    def initiate(self, world, actor_eid: int, actor_comps, gauge) -> Tuple[Optional[int], Optional[str]]:
        # ターゲットの最終確定
        return ActionMechanics.resolve_action_target(world, actor_eid, actor_comps, gauge)

    def get_initial_phase(self) -> str:
        return BattlePhase.TARGET_INDICATION

    def resolve(self, world, event, context, flow):
        attacker_comps = world.try_get_entity(event.attacker_id)
        attacker_name = attacker_comps['medal'].nickname
        part_id = attacker_comps['partlist'].parts.get(event.part_type)
        part_comps = world.try_get_entity(part_id)
        
        # 実行直前の生存チェック
        if not part_comps or part_comps['health'].hp <= 0:
            context.battle_log.append(LogBuilder.get_part_broken_attack(attacker_name))
            transition_to_phase(flow, BattlePhase.LOG_WAIT)
            return

        res = event.calculation_result
        if res and res.is_hit:
            # ダメージイベント発行
            world.add_component(event.current_target_id, DamageEventComponent(
                attacker_id=event.attacker_id,
                attacker_part=event.part_type,
                damage=res.damage,
                target_part=res.hit_part,
                is_critical=res.is_critical,
                added_effects=res.added_effects
            ))
        
        transition_to_phase(flow, BattlePhase.CUTIN_RESULT)

class SkipAction(ActionBehavior):
    def initiate(self, world, actor_eid: int, actor_comps, gauge) -> Tuple[Optional[int], Optional[str]]:
        # スキップはターゲット不要だが、続行可能として actor_eid を仮に返す
        return actor_eid, None

    def get_initial_phase(self) -> str:
        return BattlePhase.EXECUTING

    def resolve(self, world, event, context, flow):
        attacker_comps = world.try_get_entity(event.attacker_id)
        name = attacker_comps['medal'].nickname
        context.battle_log.append(LogBuilder.get_skip_action(name))
        transition_to_phase(flow, BattlePhase.LOG_WAIT)

class ActionBehaviorRegistry:
    """ActionBehaviorのカタログ"""
    _behaviors = {
        ActionType.ATTACK: AttackAction(),
        ActionType.SKIP: SkipAction()
    }
    
    @classmethod
    def get(cls, action_type: str) -> ActionBehavior:
        return cls._behaviors.get(action_type, SkipAction())