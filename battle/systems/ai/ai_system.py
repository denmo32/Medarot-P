"""エネミー思考（AI）システム"""

from core.ecs import System
from battle.constants import BattlePhase
from battle.ai.strategy import get_strategy
from battle.domain.utils import get_battle_state
from components.action_command import ActionCommandComponent

class AISystem(System):
    """
    エネミーのターンにコマンダーとしての意思決定を行う。
    結果をActionCommandComponentとして発行する。
    """
    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not context or flow.current_phase != BattlePhase.ENEMY_TURN:
            return

        eid = context.current_turn_entity_id
        if eid is None:
            flow.current_phase = BattlePhase.IDLE
            return

        # 意思決定（パーツの選択）
        strategy = get_strategy("random")
        action, part = strategy.decide_action(self.world, eid)

        # コマンドの発行
        self.world.add_component(eid, ActionCommandComponent(action, part))