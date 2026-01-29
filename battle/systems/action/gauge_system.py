"""ATBゲージ更新システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import GaugeStatus, BattlePhase
from battle.mechanics.action import ActionMechanics
from battle.mechanics.flow import transition_to_phase
from battle.mechanics.status import StatusRegistry

class GaugeSystem(BattleSystemBase):
    """ATBゲージの進行管理、および状態異常のカウントダウンを担当"""

    def update(self, dt: float):
        context, flow = self.battle_state
        if not context or not flow or flow.current_phase != BattlePhase.IDLE:
            return

        # 生存しているゲージ持ちエンティティを走査
        active_entities = [
            (eid, comps) for eid, comps in self.world.get_entities_with_components('gauge', 'defeated')
            if not comps['defeated'].is_defeated
        ]

        # 1. 行動の継続妥当性を検証（パーツ破壊による中断など）
        for eid, comps in active_entities:
            # ActionMechanics内部で破壊を検知した場合、遷移が行われる
            is_valid, message = ActionMechanics.validate_action_continuity(self.world, eid)
            if not is_valid:
                self._interrupt_action(eid, context, flow, message)
                if flow.current_phase != BattlePhase.IDLE:
                    # 割り込み（LOG_WAITなど）が発生した場合はこのフレームの処理を終了
                    return

        # 2. 待機列（コマンド選択 or 行動実行待ち）の更新
        self._update_waiting_queue(active_entities, context)
        
        # 誰かが入力待ち、または行動実行待機中であれば、ゲージ進行は一時停止（アクティブタイムバトルの仕様）
        if context.waiting_queue:
            return

        # 3. 各エンティティのゲージ進行処理
        for eid, comps in active_entities:
            self._process_entity_gauge(comps['gauge'], dt)

    def _interrupt_action(self, entity_id, context, flow, message):
        """アクション中断処理（副作用）"""
        if message:
            context.battle_log.append(message)
        transition_to_phase(flow, BattlePhase.LOG_WAIT)
        
        comps = self.world.try_get_entity(entity_id)
        if not comps or 'gauge' not in comps: return

        gauge = comps['gauge']
        current_p = gauge.progress
        gauge.status = GaugeStatus.COOLDOWN
        # 充填が進んでいるほど、放熱開始位置が低くなる（＝ペナルティが大きい）
        gauge.progress = max(0.0, 100.0 - current_p)
        gauge.selected_action = None
        gauge.selected_part = None
        
        if entity_id in context.waiting_queue:
            context.waiting_queue.remove(entity_id)

    def _update_waiting_queue(self, active_entities, context):
        """ゲージが満タンになった、または選択が必要な機体を待機列へ追加"""
        for eid, comps in active_entities:
            g = comps['gauge']
            # 行動選択が必要な状態、または充填完了（100%以上）の状態
            if g.status == GaugeStatus.ACTION_CHOICE or (g.status == GaugeStatus.CHARGING and g.progress >= 100.0):
                if eid not in context.waiting_queue:
                    context.waiting_queue.append(eid)

    def _process_entity_gauge(self, gauge, dt):
        """個別エンティティのゲージ進行と状態異常処理"""
        can_charge = True
        
        # 状態異常の更新（逆順ループで安全な削除）
        for effect in reversed(gauge.active_effects):
            behavior = StatusRegistry.get(effect.type_id)
            behavior.on_tick(effect, gauge, dt)
            
            # 停止状態など、ゲージ進行を阻害するかチェック
            if not behavior.can_charge(effect):
                can_charge = False
                
            if effect.duration <= 0:
                gauge.active_effects.remove(effect)
        
        if not can_charge:
            return

        # ゲージ進行のメインロジック
        if gauge.status == GaugeStatus.CHARGING:
            # 充填：0.0 -> 100.0
            gauge.progress = min(100.0, gauge.progress + (dt / gauge.charging_time * 100.0))
        elif gauge.status == GaugeStatus.COOLDOWN:
            # 放熱：0.0 -> 100.0 (完了で ACTION_CHOICE へ)
            gauge.progress += (dt / gauge.cooldown_time * 100.0)
            if gauge.progress >= 100.0:
                self._reset_to_choice(gauge)

    def _reset_to_choice(self, gauge):
        """放熱完了時の初期化"""
        gauge.status = GaugeStatus.ACTION_CHOICE
        gauge.progress = 0.0
        gauge.part_targets = {} 
        gauge.selected_action = None
        gauge.selected_part = None