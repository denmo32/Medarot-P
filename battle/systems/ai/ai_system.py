"""エネミー思考（AI）システム"""

from core.ecs import System
from battle.constants import BattlePhase
from battle.ai.strategy import get_strategy
from battle.domain.utils import apply_action_command

class AISystem(System):
    """
    エネミーのターン(ENEMY_TURN)に動作し、
    コマンダーとしての意思決定（どのパーツで攻撃するか）を行う。
    """
    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        # エネミー思考フェーズ以外は何もしない
        if flow.current_phase != BattlePhase.ENEMY_TURN:
            return

        eid = context.current_turn_entity_id
        if eid is None:
            flow.current_phase = BattlePhase.IDLE
            return

        # AIロジック実行（現状はランダムのみ）
        # 将来的にはStrategyComponent等を持たせて個別に設定可能にすると良い
        strategy = get_strategy("random")
        action, part = strategy.decide_action(self.world, eid)

        # 決定したコマンドを適用（共通処理）
        apply_action_command(self.world, eid, action, part)