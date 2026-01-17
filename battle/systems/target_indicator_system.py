"""ターゲット演出管理システム"""

from core.ecs import System
from battle.constants import BattlePhase, ActionType

class TargetIndicatorSystem(System):
    """
    TARGET_INDICATIONフェーズの時間管理を行う。
    演出終了後、ATTACK_DECLARATIONフェーズへ遷移し、攻撃宣言メッセージを発行する。
    """

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        if flow.current_phase != BattlePhase.TARGET_INDICATION:
            return

        # タイマー更新
        flow.phase_timer -= dt
        
        # 時間経過で次のフェーズへ
        if flow.phase_timer <= 0:
            self._transition_to_declaration(context, flow)

    def _transition_to_declaration(self, context, flow):
        """攻撃宣言フェーズへ移行し、ログを追加する"""
        event_eid = flow.processing_event_id
        event_comps = self.world.try_get_entity(event_eid)
        
        if event_comps and 'actionevent' in event_comps:
            event = event_comps['actionevent']
            
            # 攻撃アクションの場合のみ宣言を行う
            if event.action_type == ActionType.ATTACK:
                self._add_declaration_log(event, context)
                flow.current_phase = BattlePhase.ATTACK_DECLARATION
            else:
                # 攻撃以外なら即実行へ（基本ここには来ないはずだが念のため）
                flow.current_phase = BattlePhase.EXECUTING
        else:
            # イベントロスト時はIDLEへ戻す等の処理が必要だが、ここでは一旦実行フェーズへ流す
            flow.current_phase = BattlePhase.EXECUTING

    def _add_declaration_log(self, event, context):
        attacker_id = event.attacker_id
        attacker_comps = self.world.try_get_entity(attacker_id)
        
        if not attacker_comps: return

        # 攻撃者名
        attacker_name = attacker_comps['medal'].nickname
        
        # 攻撃パーツ名と特性
        part_id = attacker_comps['partlist'].parts.get(event.part_type)
        part_comps = self.world.try_get_entity(part_id) if part_id else None
        
        trait_text = ""
        if part_comps and 'attack' in part_comps:
            trait = part_comps['attack'].trait
            trait_text = f" {trait}！"
            
        context.battle_log.append(f"{attacker_name}の攻撃！{trait_text}")