"""エネミー思考（AI）システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.ai import StrategyRegistry
from components.action_command_component import ActionCommandComponent

class AISystem(BattleSystemBase):
    """エネミーの行動決定"""

    def update(self, dt: float):
        context = self.query.context
        flow = self.query.flow

        if not context or flow.current_phase != BattlePhase.ENEMY_TURN:
            return

        eid = context.current_turn_entity_id
        if eid is None:
            flow.current_phase = BattlePhase.IDLE
            return

        strategy = StrategyRegistry.get("random")
        action, part = strategy.decide_action(self.query, eid)

        self.world.add_component(eid, ActionCommandComponent(action, part))
