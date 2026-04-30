"""エネミー思考（AI）システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from domain.ai_logic import get_strategy
from components.action_command_component import ActionCommandComponent


class AISystem(BattleSystemBase):
    """エネミーの行動決定"""

    def update(self, dt: float):
        context = self.context
        flow = self.flow

        if not context or flow.current_phase != BattlePhase.ENEMY_TURN:
            return

        eid = context.current_turn_entity_id
        if eid is None:
            flow.current_phase = BattlePhase.IDLE
            return

        # 攻撃可能なパーツ（生存しており、かつ攻撃コンポーネントを持つ）を抽出
        attackable_parts = []
        comps = self.world.try_get_entity(eid)
        if comps and 'partlist' in comps:
            for p_type, p_id in comps['partlist'].parts.items():
                p_comps = self.world.try_get_entity(p_id)
                if p_comps and 'health' in p_comps and p_comps['health'].hp > 0:
                    if 'attack' in p_comps:
                        attackable_parts.append(p_type)

        strategy = get_strategy("random")
        action, part = strategy.decide_action(attackable_parts)

        self.world.add_component(eid, ActionCommandComponent(action, part))

