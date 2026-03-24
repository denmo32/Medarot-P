"""ATB ゲージ更新システム"""

from battle.systems.battle_system_base import BattleSystemBase
from battle.constants import BattlePhase, ActionType
from battle.mechanics.gauge_mechanics import GaugeMechanics
from battle.mechanics.action import ActionMechanics
from battle.mechanics.flow import PhaseTransition, FlowMechanics
from battle.mechanics.targeting import TargetingMechanics


class GaugeSystem(BattleSystemBase):
    """ATB ゲージの進行管理、および状態異常のカウントダウンを担当"""

    def update(self, dt: float):
        # バトルが停止中（ログ表示中や演出中）はゲージを進めない
        if not self.context or not self.flow or self.flow.current_phase != BattlePhase.IDLE:
            return

        # 機能停止した機体もチェック対象（待機キュー中の中断判定のため）
        all_entities = self.world.get_entities_with_components('gauge', 'defeated')

        # 1. 状態異常の更新（機能停止していない機体のみ）
        for _, comps in all_entities:
            if comps['defeated'].is_defeated:
                continue
            gauge = comps['gauge']
            if gauge.active_effects:
                gauge.active_effects = GaugeMechanics.get_updated_effects(gauge.active_effects, dt)

        # 2. 中断判定とゲージ進行
        # 誰かが行動待機中の場合は、時間は進めるがゲージ増加は行わない
        time_step = 0.0 if self.context.waiting_queue else dt

        for eid, comps in all_entities:
            gauge = comps['gauge']

            # 機能停止している場合は、待機キューに入っていれば削除
            if comps['defeated'].is_defeated:
                if eid in self.context.waiting_queue:
                    FlowMechanics.manage_queue(self.context, eid, False)
                continue

            # 行動の継続妥当性を検証（パーツ破壊チェックなど）
            # System 側で必要なデータを抽出して純粋関数に渡す
            actor_comps = self.world.try_get_entity(eid)
            actor_name = actor_comps['medal'].nickname if actor_comps and 'medal' in actor_comps else "Unknown"

            # 実行予定パーツの生存チェック
            is_actor_part_alive = True
            if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
                is_actor_part_alive = TargetingMechanics.is_part_alive(self.world, eid, gauge.selected_part)

            # ターゲット部位の生存チェック
            is_target_part_alive = True
            target_data = gauge.part_targets.get(gauge.selected_part)
            if target_data:
                target_id, target_part = target_data
                is_target_part_alive = TargetingMechanics.is_part_alive(self.world, target_id, target_part)

            interruption = ActionMechanics.validate_action_continuity(
                gauge_status=gauge.status,
                gauge_progress=gauge.progress,
                gauge_selected_action=gauge.selected_action,
                gauge_selected_part=gauge.selected_part,
                gauge_part_targets=gauge.part_targets,
                actor_name=actor_name,
                is_actor_part_alive=is_actor_part_alive,
                is_target_part_alive=is_target_part_alive
            )

            if not interruption.is_valid:
                comps = self.world.try_get_entity(eid)
                if comps and 'gauge' in comps:
                    ActionMechanics.apply_gauge_reset(comps['gauge'], interruption.reset_data)
                FlowMechanics.manage_queue(self.context, eid, False)
                FlowMechanics.apply_transition(self.world, PhaseTransition(BattlePhase.LOG_WAIT, logs=[interruption.message]))
                # ログ表示フェーズに入るため、このフレームの処理を打ち切る
                return

            # ゲージ進行計算
            summary = GaugeMechanics.calculate_tick(gauge, time_step)

            # ゲージ値の更新
            gauge.progress = summary.new_progress

            # 放熱完了のチェックとリセット
            if summary.is_cooldown_finished:
                reset = ActionMechanics.get_choice_reset_data()
                comps = self.world.try_get_entity(eid)
                if comps and 'gauge' in comps:
                    ActionMechanics.apply_gauge_reset(comps['gauge'], reset)
                # リセット後は待機列に入る必要がない
                FlowMechanics.manage_queue(self.context, eid, False)
            else:
                # 充填完了、または行動選択待ちならキューに追加
                FlowMechanics.manage_queue(self.context, eid, summary.should_be_in_queue)
