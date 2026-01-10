"""行動開始起案システム"""

import random
from core.ecs import System
from components.battle_flow import BattleFlowComponent
from components.action_event import ActionEventComponent
from battle.utils import get_closest_target_by_gauge
from battle.constants import GaugeStatus, ActionType, PartType, TeamType, BattlePhase, TraitType

class ActionInitiationSystem(System):
    """
    1. 行動開始の起案システム
    チャージ完了したエンティティがあれば、ActionEventを生成してフェーズをEXECUTINGに移行する。
    """
    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        # IDLE状態以外では新たな行動を開始しない
        if flow.current_phase != BattlePhase.IDLE:
            return
        
        if not context.waiting_queue:
            return

        # 待機列先頭のエンティティをチェック
        actor_eid = context.waiting_queue[0]
        if actor_eid not in self.world.entities:
            context.waiting_queue.pop(0)
            return

        actor_comps = self.world.entities[actor_eid]
        gauge = actor_comps['gauge']
        
        # チャージ完了（100%）しているか確認
        if gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0:
            self._initiate_action(actor_eid, actor_comps, gauge, flow, context)

    def _initiate_action(self, actor_eid, actor_comps, gauge, flow, context):
        # ターゲット確定
        target_id = None
        target_part = None
        
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
            if part_id and part_id in self.world.entities:
                attack_comp = self.world.entities[part_id].get('attack')
                target_id, target_part = self._determine_target(actor_eid, actor_comps, gauge, attack_comp)
        
        # ActionEventエンティティ生成
        event_eid = self.world.create_entity()
        self.world.add_component(event_eid, ActionEventComponent(
            attacker_id=actor_eid,
            action_type=gauge.selected_action,
            part_type=gauge.selected_part,
            target_id=target_id,
            target_part=target_part
        ))
        
        # フェーズ移行
        flow.current_phase = BattlePhase.EXECUTING
        flow.processing_event_id = event_eid
        
        # 待機列から削除
        if context.waiting_queue and context.waiting_queue[0] == actor_eid:
            context.waiting_queue.pop(0)

    def _determine_target(self, eid, comps, gauge, attack_comp):
        target_id = None
        target_part = None

        # 近接攻撃特性の判定（サンダーを追加）
        if attack_comp and attack_comp.trait in [TraitType.SWORD, TraitType.HAMMER, TraitType.THUNDER]:
            # 直前ターゲット：現在のアイコン座標が最も中央に近い敵を狙う
            target_id = get_closest_target_by_gauge(self.world, comps['team'].team_type)
            # 直前ターゲットの場合、この時点で狙う部位を決定する（ランダム）
            if target_id:
                target_part = self._select_random_alive_part(target_id)
        else:
            # 事前ターゲット（Personalityによって設定されたもの）
            if gauge.selected_part:
                target_data = gauge.part_targets.get(gauge.selected_part)
                if target_data:
                    target_id, target_part = target_data
        
        # 救済措置（対象が既に倒れている、または見つからない場合）
        if not target_id or target_id not in self.world.entities or self.world.entities[target_id]['defeated'].is_defeated:
            target_id = self._get_fallback_target_id(comps['team'].team_type)
            if target_id:
                target_part = self._select_random_alive_part(target_id)

        return target_id, target_part

    def _get_fallback_target_id(self, my_team):
        target_team = TeamType.ENEMY if my_team == TeamType.PLAYER else TeamType.PLAYER
        alive = [teid for teid, tcomps in self.world.get_entities_with_components('team', 'defeated') 
                 if tcomps['team'].team_type == target_team and not tcomps['defeated'].is_defeated]
        return random.choice(alive) if alive else None

    def _select_random_alive_part(self, target_id):
        """対象の生存パーツからランダムに1つ選ぶ"""
        if target_id not in self.world.entities:
            return None
        
        t_comps = self.world.entities[target_id]
        alive_parts = []
        for p_type, p_id in t_comps['partlist'].parts.items():
            if self.world.entities[p_id]['health'].hp > 0:
                alive_parts.append(p_type)
        
        return random.choice(alive_parts) if alive_parts else PartType.HEAD