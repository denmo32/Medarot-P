"""行動解決システム"""

from core.ecs import System
from components.battle_component import DamageEventComponent
from battle.constants import ActionType, BattlePhase
from battle.mechanics.flow import transition_to_phase, get_battle_state
from battle.mechanics.log import LogBuilder
from battle.mechanics.action import ActionMechanics

class ActionResolutionSystem(System):
    """計算済みの ActionEvent に基づき、世界に結果（ダメージ等）を反映する"""
    
    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not flow or flow.current_phase != BattlePhase.EXECUTING:
            return
        
        event_eid = flow.processing_event_id
        event_comps = self.get_comps(event_eid, 'actionevent') if event_eid is not None else None
        
        if not event_comps:
            transition_to_phase(flow, BattlePhase.IDLE)
            return

        self._resolve_action(event_comps['actionevent'], context, flow)
        
        # カットイン結果待ちフェーズに移行していないなら、このイベントは完了
        if flow.current_phase != BattlePhase.CUTIN_RESULT:
            self.world.delete_entity(event_eid)
            flow.processing_event_id = None

    def _resolve_action(self, event, context, flow):
        attacker_comps = self.get_comps(event.attacker_id, 'medal', 'partlist', 'gauge')
        if not attacker_comps: return

        if event.action_type == ActionType.ATTACK:
            self._handle_attack_resolution(event, attacker_comps, context)
            transition_to_phase(flow, BattlePhase.CUTIN_RESULT)
        elif event.action_type == ActionType.SKIP:
            context.battle_log.append(LogBuilder.get_skip_action(attacker_comps['medal'].nickname))
            transition_to_phase(flow, BattlePhase.LOG_WAIT)

        # ゲージの初期化（放熱へ）
        ActionMechanics.reset_to_cooldown(attacker_comps['gauge'])

    def _handle_attack_resolution(self, event, attacker_comps, context):
        attacker_name = attacker_comps['medal'].nickname
        part_id = attacker_comps['partlist'].parts.get(event.part_type)
        part_comps = self.world.try_get_entity(part_id)
        
        # 実行時のパーツ破壊チェック
        if not part_comps or part_comps['health'].hp <= 0:
            context.battle_log.append(LogBuilder.get_part_broken_attack(attacker_name))
            return

        res = event.calculation_result
        if res is None or not res.is_hit:
            return
            
        # ダメージイベントの発行
        self.world.add_component(event.current_target_id, DamageEventComponent(
            attacker_id=event.attacker_id,
            attacker_part=event.part_type,
            damage=res.damage,
            target_part=res.hit_part,
            is_critical=res.is_critical,
            added_effects=res.added_effects
        ))