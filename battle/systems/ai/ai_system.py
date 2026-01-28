"""エネミー思考（AI）システム"""

from core.ecs import System
from battle.constants import BattlePhase
from battle.mechanics.ai import StrategyRegistry
from battle.mechanics.flow import get_battle_state
from components.action_command_component import ActionCommandComponent

class AISystem(System):
    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not context or flow.current_phase != BattlePhase.ENEMY_TURN:
            return

        eid = context.current_turn_entity_id
        if eid is None:
            flow.current_phase = BattlePhase.IDLE
            return

        strategy = StrategyRegistry.get("random")
        action, part = strategy.decide_action(self.world, eid)

        self.world.add_component(eid, ActionCommandComponent(action, part))