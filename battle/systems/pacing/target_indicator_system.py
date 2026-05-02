"""ターゲット演出のフロー制御システム"""

from battle.systems.base.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase
from domain.flow_logic import resolve_indicator_transition, PhaseTransition


class TargetIndicatorSystem(BattleSystemBase):
    """ターゲット指示演出の進行管理"""

    def update(self, dt: float):
        context = self.context
        flow = self.flow

        if not context or flow.current_phase != BattlePhase.TARGET_INDICATION:
            return

        flow.phase_timer -= dt

        if flow.phase_timer <= 0:
            # イベントコンポーネントを取得
            event_comps = self.world.try_get_entity(flow.processing_event_id)
            if not event_comps or 'actionevent' not in event_comps:
                self.apply_transition(PhaseTransition(next_phase=BattlePhase.IDLE))
                return

            event = event_comps['actionevent']

            # 攻撃者情報を取得
            attacker_comps = self.world.try_get_entity(event.attacker_id)
            attacker_name = attacker_comps['medal'].nickname if attacker_comps and 'medal' in attacker_comps else "Unknown"

            # 攻撃パーツ情報を取得
            attack_trait = ""
            attack_skill_type = ""
            if attacker_comps and 'partlist' in attacker_comps:
                part_id = attacker_comps['partlist'].parts.get(event.part_type)
                if part_id:
                    p_comps = self.world.try_get_entity(part_id)
                    if p_comps and 'attack' in p_comps:
                        attack_trait = p_comps['attack'].trait
                        attack_skill_type = p_comps['attack'].skill_type

            # 次の遷移情報を Domain から取得
            transition = resolve_indicator_transition(
                event_action_type=event.action_type,
                attacker_name=attacker_name,
                attack_trait=attack_trait,
                attack_skill_type=attack_skill_type
            )
            # 副作用を適用
            self.apply_transition(transition)
