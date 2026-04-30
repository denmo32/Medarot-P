"""ATB ゲージ更新システム"""

from typing import Dict, Any
from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase, ActionType
from domain.constants import GaugeStatus
from domain.gauge_logic import calculate_tick, get_updated_effects
from domain.action_logic import get_cooldown_reset_data, get_choice_reset_data
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
                self._remove_from_queue(eid)
                continue

            # 行動の継続妥当性を検証
            actor_name = self.get_entity_name(eid)
            is_actor_part_alive = True
            if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
                is_actor_part_alive = self._is_part_alive(eid, gauge.selected_part)

            is_target_part_alive = True
            target_data = gauge.part_targets.get(gauge.selected_part)
            if target_data:
                target_id, target_part = target_data
                is_target_part_alive = self._is_part_alive(target_id, target_part)

            # 中断判定ロジックを System 内に展開（元 validate_action_continuity）
            interruption_msg = None
            if gauge.status in (GaugeStatus.CHARGING, GaugeStatus.ACTION_CHOICE):
                if gauge.selected_action == ActionType.ATTACK and gauge.selected_part and not is_actor_part_alive:
                    interruption_msg = f"{actor_name}の予約パーツは破壊された！"
                elif target_data and not is_target_part_alive:
                    interruption_msg = f"{actor_name}はターゲットロストした！"

            if interruption_msg:
                reset = get_cooldown_reset_data(gauge.progress)
                self._apply_gauge_reset(gauge, reset)
                self._remove_from_queue(eid)
                self._apply_transition(PhaseTransition(BattlePhase.LOG_WAIT, logs=[interruption_msg]))
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
                self._apply_gauge_reset(gauge, reset)
                self._remove_from_queue(eid)
            else:
                # 充填完了、または行動選択待ちならキューに追加
                self._manage_queue(eid, summary.should_be_in_queue)

    # --- Local Helpers ---

    def _manage_queue(self, eid: int, should_add: bool):
        if not self.context: return
        queue = self.context.waiting_queue
        if should_add and eid not in queue: queue.append(eid)
        elif not should_add and eid in queue: queue.remove(eid)

    def _remove_from_queue(self, eid: int):
        self._manage_queue(eid, False)

    def _apply_transition(self, transition: PhaseTransition):
        flow = self.flow
        ctx = self.context
        if not flow: return
        flow.current_phase = transition.next_phase
        flow.phase_timer = transition.timer
        if transition.actor_id is not None: flow.active_actor_id = transition.actor_id
        if transition.event_id is not None: flow.processing_event_id = transition.event_id
        if transition.logs and ctx: ctx.battle_log.extend(transition.logs)

    def _is_part_alive(self, eid: int, part_type: str) -> bool:
        comps = self.world.try_get_entity(eid)
        if not comps or (comps.get('defeated') and comps['defeated'].is_defeated): return False
        pid = comps['partlist'].parts.get(part_type)
        if pid is None: return False
        p_comps = self.world.try_get_entity(pid)
        return bool(p_comps and 'health' in p_comps and p_comps['health'].hp > 0)

    def _apply_gauge_reset(self, gauge, reset_data):
        gauge.status = reset_data.status
        gauge.progress = reset_data.progress
        if reset_data.clear_selection:
            gauge.selected_action = None
            gauge.selected_part = None
            gauge.part_targets = {}

