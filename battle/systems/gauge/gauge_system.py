"""ATB ゲージ更新システム"""

from typing import Dict, Any
from battle.systems.base.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase, ActionType
from domain.constants import GaugeStatus
from domain.gauge_logic import calculate_tick, get_updated_effects
from domain.action_logic import (
    get_cooldown_reset_data, 
    get_choice_reset_data, 
    check_action_interruption
)
from domain.flow_logic import PhaseTransition


class GaugeSystem(BattleSystemBase):
    """ATB ゲージの進行管理、および状態異常のカウントダウンを担当"""

    def update(self, dt: float):
        # バトルが停止中（ログ表示中や演出中）はゲージを進めない
        if not self.is_ready(BattlePhase.IDLE):
            return

        # 機能停止した機体もチェック対象（待機キュー中の中断判定のため）
        all_entities = self.world.get_entities_with_components('gauge', 'defeated')

        # 1. 状態異常の更新（機能停止していない機体のみ）
        for _, comps in all_entities:
            if comps['defeated'].is_defeated:
                continue
            gauge = comps['gauge']
            if gauge.active_effects:
                gauge.active_effects = get_updated_effects(gauge.active_effects, dt)

        # 2. 中断判定とゲージ進行
        # 誰かが行動待機中の場合、または開始演出が終わっていない場合は、時間は進めるがゲージ増加は行わない
        time_step = dt
        if self.context.waiting_queue or not self.flow.is_opening_done:
            time_step = 0.0

        for eid, comps in all_entities:
            gauge = comps['gauge']

            # 機能停止している場合は、待機キューに入っていれば削除
            if comps['defeated'].is_defeated:
                self.remove_from_queue(eid)
                continue

            # 行動の継続妥当性を検証
            actor_name = self.get_entity_name(eid)
            is_actor_part_alive = True
            if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
                is_actor_part_alive = self.is_part_alive(eid, gauge.selected_part)

            is_target_part_alive = True
            target_data = gauge.part_targets.get(gauge.selected_part)
            if target_data:
                target_id, target_part = target_data
                is_target_part_alive = self.is_part_alive(target_id, target_part)

            # 中断判定
            interruption = check_action_interruption(
                status=gauge.status,
                selected_action=gauge.selected_action,
                selected_part=gauge.selected_part,
                is_actor_part_alive=is_actor_part_alive,
                target_data=target_data,
                is_target_part_alive=is_target_part_alive,
                actor_name=actor_name
            )

            if interruption.is_interrupted:
                reset = get_cooldown_reset_data(gauge.progress)
                self.apply_gauge_reset(gauge, reset)
                self.remove_from_queue(eid)
                self.apply_transition(PhaseTransition(BattlePhase.LOG_WAIT, logs=[interruption.message]))
                return

            # ゲージ進行計算
            summary = calculate_tick(
                status=gauge.status,
                progress=gauge.progress,
                charging_time=gauge.charging_time,
                cooldown_time=gauge.cooldown_time,
                active_effects=gauge.active_effects,
                dt=time_step
            )

            # ゲージ値の更新
            gauge.progress = summary.new_progress

            # 放熱完了のチェックとリセット
            if summary.is_cooldown_finished:
                reset = get_choice_reset_data()
                self.apply_gauge_reset(gauge, reset)
                self.remove_from_queue(eid)
            else:
                # 充填完了、または行動選択待ちならキューに追加
                self._manage_queue(eid, summary.should_be_in_queue)

    # --- Local Helpers ---

    def _manage_queue(self, eid: int, should_add: bool):
        if not self.context: return
        queue = self.context.waiting_queue
        if should_add and eid not in queue: queue.append(eid)
        elif not should_add and eid in queue: queue.remove(eid)
