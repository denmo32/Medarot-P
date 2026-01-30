"""行動解決システム"""

from battle.systems.battle_system_base import BattleSystemBase
from components.battle_component import DamageEventComponent
from battle.constants import ActionType, BattlePhase
from battle.mechanics.flow import transition_to_phase
from battle.mechanics.log import LogBuilder
from battle.mechanics.action import ActionMechanics

class ActionResolutionSystem(BattleSystemBase):
    """
    演出が終了した段階で呼ばれ、計算済みの ActionEvent 結果を世界（HPやステータス）に反映する。
    """
    def update(self, dt: float):
        if not self.flow or self.flow.current_phase != BattlePhase.EXECUTING:
            return
        
        event_eid = self.flow.processing_event_id
        event_comps = self.get_comps(event_eid, 'actionevent') if event_eid is not None else None
        
        if not event_comps:
            transition_to_phase(self.flow, BattlePhase.IDLE)
            return

        # 行動の解決
        self._resolve_action(event_comps['actionevent'])
        
        # 解決後、フェーズが CUTIN_RESULT 等に遷移していない場合はクリーンアップ
        if self.flow.current_phase != BattlePhase.CUTIN_RESULT:
            self.world.delete_entity(event_eid)
            self.flow.processing_event_id = None

    def _resolve_action(self, event):
        """アクション種別に応じた解決"""
        attacker_comps = self.get_comps(event.attacker_id, 'medal', 'partlist', 'gauge')
        if not attacker_comps: return

        if event.action_type == ActionType.ATTACK:
            self._apply_attack_impact(event, attacker_comps)
            transition_to_phase(self.flow, BattlePhase.CUTIN_RESULT)
        elif event.action_type == ActionType.SKIP:
            name = attacker_comps['medal'].nickname
            self.context.battle_log.append(LogBuilder.get_skip_action(name))
            transition_to_phase(self.flow, BattlePhase.LOG_WAIT)

        # 実行後は常に放熱状態へリセット
        ActionMechanics.reset_to_cooldown(attacker_comps['gauge'])

    def _apply_attack_impact(self, event, attacker_comps):
        """攻撃ヒット時の副作用（ダメージイベント発行など）を適用"""
        attacker_name = attacker_comps['medal'].nickname
        part_id = attacker_comps['partlist'].parts.get(event.part_type)
        part_comps = self.world.try_get_entity(part_id)
        
        # 実行直前の最終破壊チェック（相打ちなどのケース用）
        if not part_comps or part_comps['health'].hp <= 0:
            self.context.battle_log.append(LogBuilder.get_part_broken_attack(attacker_name))
            return

        res = event.calculation_result
        if res is None or not res.is_hit:
            return # ミス時はダメージイベントを発行しない
            
        # ダメージ発生を伝えるコンポーネントを追加（DamageSystemが処理）
        self.world.add_component(event.current_target_id, DamageEventComponent(
            attacker_id=event.attacker_id,
            attacker_part=event.part_type,
            damage=res.damage,
            target_part=res.hit_part,
            is_critical=res.is_critical,
            added_effects=res.added_effects
        ))