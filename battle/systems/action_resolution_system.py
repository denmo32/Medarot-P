"""行動解決システム"""

from core.ecs import System
from components.battle import DamageEventComponent
from battle.constants import ActionType, BattlePhase
from battle.utils import reset_gauge_to_cooldown

class ActionResolutionSystem(System):
    """
    2. 行動解決システム
    事前に計算された ActionEvent の結果に基づき、DamageEventを発行する。
    """
    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        if flow.current_phase != BattlePhase.EXECUTING:
            return
        
        event_eid = flow.processing_event_id
        event_comps = self.world.try_get_entity(event_eid) if event_eid is not None else None
        
        if not event_comps or 'actionevent' not in event_comps:
            flow.current_phase = BattlePhase.IDLE
            flow.processing_event_id = None
            return

        event = event_comps['actionevent']
        
        # アクションの実行
        self._resolve_action(event, context, flow)
        
        # CUTIN_RESULTへ移行する場合はイベントをまだ削除しない
        if flow.current_phase != BattlePhase.CUTIN_RESULT:
            self.world.delete_entity(event_eid)
            flow.processing_event_id = None

    def _resolve_action(self, event, context, flow):
        attacker_id = event.attacker_id
        attacker_comps = self.world.try_get_entity(attacker_id)
        
        if not attacker_comps: return

        if event.action_type == ActionType.ATTACK:
            self._handle_attack_action(event, attacker_comps, context)
            flow.current_phase = BattlePhase.CUTIN_RESULT
            
        elif event.action_type == ActionType.SKIP:
            context.battle_log.append(f"{attacker_comps['medal'].nickname}は行動をスキップ！")
            flow.current_phase = BattlePhase.LOG_WAIT

        # クールダウンへ
        if 'gauge' in attacker_comps:
            reset_gauge_to_cooldown(attacker_comps['gauge'])

    def _handle_attack_action(self, event, attacker_comps, context):
        attacker_name = attacker_comps['medal'].nickname
        
        # 1. 自身の攻撃パーツ生存チェック
        part_id = attacker_comps['partlist'].parts.get(event.part_type)
        part_comps = self.world.try_get_entity(part_id) if part_id is not None else None
        if not part_comps or part_comps['health'].hp <= 0:
            context.battle_log.append(f"{attacker_name}の攻撃！ しかしパーツが破損している！")
            return

        # 2. 事前計算結果の適用
        res = event.calculation_result
        if res is None:
            # 計算が行われていない（ターゲットロスト等）
            context.battle_log.append(f"{attacker_name}はターゲットを見失った！")
            return

        if not res['is_hit']:
            context.pending_logs.append("攻撃を回避！")
            return
            
        # ログのキューイング
        if res['is_critical']:
            context.pending_logs.append("クリティカルヒット！")
        elif res['is_defense']:
            context.pending_logs.append("攻撃を防御！")
        else:
            context.pending_logs.append("防御突破！クリーンヒット！")
            
        # ダメージイベント発行
        # 修正: event.target_id -> event.current_target_id
        self.world.add_component(event.current_target_id, DamageEventComponent(
            attacker_id=event.attacker_id,
            attacker_part=event.part_type,
            damage=res['damage'],
            target_part=res['hit_part'],
            is_critical=res['is_critical'],
            stop_duration=res['stop_duration']
        ))