"""ターゲット演出のフロー制御システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from battle.mechanics.flow import FlowMechanics

class TargetIndicatorSystem(BattleSystemBase):
    """ターゲット指示演出の進行管理"""

    def update(self, dt: float):
        context = self.query.context
        flow = self.query.flow

        if not context or flow.current_phase != BattlePhase.TARGET_INDICATION:
            return

        flow.phase_timer -= dt

        if flow.phase_timer <= 0:
            # イベントコンポーネントを取得
            event_comps = self.world.try_get_entity(flow.processing_event_id)
            if not event_comps or 'actionevent' not in event_comps:
                self.command.apply_phase_transition(FlowMechanics.resolve_indicator_transition("", "", "", ""))
                return
            
            event = event_comps['actionevent']
            
            # 攻撃者情報を取得
            attacker_comps = self.world.try_get_entity(event.attacker_id)
            attacker_name = attacker_comps['medal'].nickname if attacker_comps and 'medal' in attacker_comps else "Unknown"
            
            # 攻撃パーツ情報を取得
            part_comps = self.query.get_part_components(event.attacker_id, event.part_type, 'attack')
            attack_trait = part_comps['attack'].trait if part_comps else ""
            attack_skill_type = part_comps['attack'].skill_type if part_comps else ""
            
            # 次の遷移情報を Mechanics から取得（純粋関数にデータを渡す）
            transition = FlowMechanics.resolve_indicator_transition(
                event_action_type=event.action_type,
                attacker_name=attacker_name,
                attack_trait=attack_trait,
                attack_skill_type=attack_skill_type
            )
            # 副作用を適用
            self.command.apply_phase_transition(transition)
