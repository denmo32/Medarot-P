"""ATBゲージ更新システム"""

from core.ecs import System
from battle.constants import GaugeStatus, BattlePhase, ActionType
from battle.utils import interrupt_gauge_return_home

class GaugeSystem(System):
    """ATBゲージの進行管理、およびチャージ中のアクション有効性監視を担当"""
    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        if flow.current_phase != BattlePhase.IDLE:
            return

        gauge_entities = self.world.get_entities_with_components('gauge', 'defeated', 'medal', 'partlist')

        # 1. チャージ中の割り込みチェック
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            if comps['gauge'].status == GaugeStatus.CHARGING:
                self._check_interruption(eid, comps, comps['gauge'], context, flow)

        if flow.current_phase == BattlePhase.LOG_WAIT:
            return

        # 2. 待機列（ACTION_CHOICE / CHARGE完了）の機体を確認・更新
        self._update_waiting_queue(gauge_entities, context)

        # 3. 処理待ちがいる場合はゲージ停止（ウェイト式）
        if context.waiting_queue:
            return

        # 4. ゲージ進行処理
        self._advance_gauges(gauge_entities, dt, context)

    def _check_interruption(self, eid, comps, gauge, context, flow):
        """チャージ中の継続条件をチェックし、満たさない場合は中断させる"""
        actor_name = comps['medal'].nickname
        
        # 1. 自身の予約パーツが破壊されたか
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            p_id = comps['partlist'].parts.get(gauge.selected_part)
            if not p_id or self.world.entities[p_id]['health'].hp <= 0:
                self._interrupt(eid, gauge, context, flow, f"{actor_name}の予約パーツは破壊された！")
                return

        # 2. ターゲットがロストしたか（事前ターゲットの場合のみ）
        target_data = gauge.part_targets.get(gauge.selected_part)
        if target_data:
            target_id, target_part_type = target_data
            lost = False
            
            if target_id not in self.world.entities or self.world.entities[target_id]['defeated'].is_defeated:
                lost = True
            else:
                t_part_id = self.world.entities[target_id]['partlist'].parts.get(target_part_type)
                if not t_part_id or self.world.entities[t_part_id]['health'].hp <= 0:
                    lost = True
            
            if lost:
                self._interrupt(eid, gauge, context, flow, f"{actor_name}はターゲットロストした！")
                return

    def _interrupt(self, eid, gauge, context, flow, message):
        """アクションを中断し、その地点からホームへ戻る"""
        context.battle_log.append(message)
        flow.current_phase = BattlePhase.LOG_WAIT
        
        interrupt_gauge_return_home(gauge)
        
        if eid in context.waiting_queue:
            context.waiting_queue.remove(eid)

    def _update_waiting_queue(self, gauge_entities, context):
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            # 行動選択待ち状態ならキューへ
            if comps['gauge'].status == GaugeStatus.ACTION_CHOICE:
                if eid not in context.waiting_queue:
                    context.waiting_queue.append(eid)

    def _advance_gauges(self, gauge_entities, dt, context):
        for eid, comps in gauge_entities:
            if comps['defeated'].is_defeated: continue
            gauge = comps['gauge']
            
            if gauge.stop_timer > 0:
                gauge.stop_timer = max(0.0, gauge.stop_timer - dt)
                continue
            
            if gauge.status == GaugeStatus.CHARGING:
                gauge.progress += dt / gauge.charging_time * 100.0
                if gauge.progress >= 100.0:
                    gauge.progress = 100.0
                    if eid not in context.waiting_queue:
                        context.waiting_queue.append(eid)
            
            elif gauge.status == GaugeStatus.COOLDOWN:
                gauge.progress += dt / gauge.cooldown_time * 100.0
                if gauge.progress >= 100.0:
                    gauge.progress = 0.0
                    gauge.status = GaugeStatus.ACTION_CHOICE
                    gauge.part_targets = {} 
                    if eid not in context.waiting_queue:
                        context.waiting_queue.append(eid)