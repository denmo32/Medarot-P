"""ターゲット演出管理システム"""

from core.ecs import System
from battle.constants import BattlePhase, ActionType
from battle.service.log_service import LogService
from battle.domain.skill_registry import SkillRegistry
from battle.service.flow_service import transition_to_phase, get_battle_state

class TargetIndicatorSystem(System):
    """
    TARGET_INDICATIONフェーズの時間管理を行う。
    演出終了後、ATTACK_DECLARATIONフェーズへ遷移し、攻撃宣言メッセージを発行する。
    """
    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not context or flow.current_phase != BattlePhase.TARGET_INDICATION:
            return

        flow.target_line_offset += dt
        flow.phase_timer -= dt
        
        if flow.phase_timer <= 0:
            self._transition_to_declaration(context, flow)

    def _transition_to_declaration(self, context, flow):
        event_eid = flow.processing_event_id
        event_comps = self.world.try_get_entity(event_eid)
        
        if event_comps and 'actionevent' in event_comps:
            event = event_comps['actionevent']
            if event.action_type == ActionType.ATTACK:
                self._add_declaration_log(event, context)
                transition_to_phase(flow, BattlePhase.ATTACK_DECLARATION)
            else:
                transition_to_phase(flow, BattlePhase.EXECUTING)
        else:
            transition_to_phase(flow, BattlePhase.EXECUTING)

    def _add_declaration_log(self, event, context):
        attacker_id = event.attacker_id
        attacker_comps = self.world.try_get_entity(attacker_id)
        if not attacker_comps: return

        attacker_name = attacker_comps['medal'].nickname
        trait_text, skill_name = "", "攻撃"
        
        part_id = attacker_comps['partlist'].parts.get(event.part_type)
        if part_id:
            part_comps = self.world.try_get_entity(part_id)
            if part_comps and 'attack' in part_comps:
                attack_comp = part_comps['attack']
                trait_text = f" {attack_comp.trait}！"
                # スキル名の取得はRegistryへ委譲
                skill_name = SkillRegistry.get(attack_comp.skill_type).name
        
        context.battle_log.append(LogService.get_attack_declaration(attacker_name, skill_name, trait_text))