"""行動解決システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.flow import PhaseTransition
from battle.mechanics.action_behavior import ActionBehaviorRegistry

class ActionResolutionSystem(BattleSystemBase):
    """
    演出が終了した段階で呼ばれ、ActionEvent 結果を世界に反映する。
    """
    def update(self, dt: float):
        flow = self.query.flow
        if not flow or flow.current_phase != BattlePhase.EXECUTING:
            return

        event_eid = flow.processing_event_id
        event_comps = self.world.try_get_entity(event_eid) if event_eid is not None else None

        if not event_comps or 'actionevent' not in event_comps:
            self.command.apply_phase_transition(PhaseTransition(next_phase=BattlePhase.IDLE))
            return

        # 行動の解決（Mechanics への委譲）
        event = event_comps['actionevent']
        attacker_comps = self.world.try_get_entity(event.attacker_id)

        if attacker_comps and 'gauge' in attacker_comps:
            behavior = ActionBehaviorRegistry.get(event.action_type)

            # 1. 結果オブジェクトの取得
            result = behavior.resolve(self.query, event, self.query.context)

            # 2. 世界への適用（副作用：ダメージ付与、ゲージリセット、フェーズ遷移）
            self.command.apply_resolution_result(event.attacker_id, result, event_id=event_eid)

        # 演出結果表示（CUTIN_RESULT）やログ待ち（LOG_WAIT）以外なら、イベントを削除してクリーンアップ
        if flow.current_phase not in [BattlePhase.CUTIN_RESULT, BattlePhase.LOG_WAIT]:
            self.command.delete_event(event_eid)
