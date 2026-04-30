"""行動開始起案システム"""

from typing import Optional, Dict, Any
from battle.systems.battle_system_base import BattleSystemBase
from components.action_event_component import ActionEventComponent
from domain.constants import GaugeStatus, ActionType, PartType
from battle.constants import BattlePhase, BattleTiming
from domain.action_logic import get_action_behavior, get_cooldown_reset_data, InitiateParams
from domain.log_logic import get_target_lost
from domain.flow_logic import PhaseTransition
from domain.combat_logic import (
    calculate_adjusted_stats, get_defensive_penalty, calculate_combat_result,
    MedalParams, AttackParams, LegsStats
)
from battle.systems.utils.targeting_helpers import TargetResolverFactory


class ActionInitiationSystem(BattleSystemBase):
    """
    充填が完了したエンティティに対し、ActionEvent を生成してバトルフローを開始する。
    """
    def update(self, dt: float):
        context = self.context
        flow = self.flow

        if not context or flow.current_phase != BattlePhase.IDLE or not context.waiting_queue:
            return

        actor_eid = context.waiting_queue[0]
        actor_comps = self.world.try_get_entity(actor_eid)

        # エンティティが存在しない、または機能停止している場合はキューから削除
        defeated = actor_comps.get('defeated') if actor_comps else None
        if not actor_comps or (defeated and defeated.is_defeated):
            self._remove_from_queue(actor_eid)
            return

        required = ['gauge', 'team', 'partlist', 'medal']
        if not all(k in actor_comps for k in required):
            self._remove_from_queue(actor_eid)
            return

        gauge = actor_comps['gauge']
        # 充填完了チェック
        if gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0:
            self._initiate_action(actor_eid, actor_comps, gauge)

    def _initiate_action(self, actor_eid: int, actor_comps: dict, gauge):
        """行動開始の具体処理"""
        # 行動種別に応じた振る舞いを取得
        behavior = get_action_behavior(gauge.selected_action)

        # 1. 実行パーツの生存チェック
        is_actor_part_alive = True
        attack_trait = ""
        if gauge.selected_action == ActionType.ATTACK and gauge.selected_part:
            is_actor_part_alive = self._is_part_alive(actor_eid, gauge.selected_part)
            # 攻撃パーツの特性情報を取得
            if 'partlist' in actor_comps:
                part_id = actor_comps['partlist'].parts.get(gauge.selected_part)
                if part_id:
                    p_comps = self.world.try_get_entity(part_id)
                    if p_comps and 'attack' in p_comps:
                        attack_trait = p_comps['attack'].trait

        # 2. TargetResolver によるターゲット解決
        resolver = TargetResolverFactory.get(attack_trait)
        resolved_target_id, resolved_target_part = resolver.resolve(
            actor_eid=actor_eid,
            selected_part=gauge.selected_part,
            world=self.world
        )

        # 3. パラメータ構築
        params = InitiateParams(
            selected_action=gauge.selected_action,
            selected_part=gauge.selected_part,
            is_actor_part_alive=is_actor_part_alive,
            attack_trait=attack_trait,
            resolved_target_id=resolved_target_id,
            resolved_target_part=resolved_target_part
        )

        target_id, target_part = behavior.initiate(params)

        # ターゲットロスト時の中断処理
        if not target_id:
            msg = get_target_lost(actor_comps['medal'].nickname)
            reset = get_cooldown_reset_data(gauge.progress, use_penalty=True)

            if 'gauge' in actor_comps:
                self._apply_gauge_reset(actor_comps['gauge'], reset)
            
            self._remove_from_queue(actor_eid)
            self._apply_transition(PhaseTransition(next_phase=BattlePhase.LOG_WAIT, logs=[msg]))
            return

        # 2. ActionEvent の生成
        event_eid = self.world.create_entity()
        event = ActionEventComponent(
            attacker_id=actor_eid,
            action_type=gauge.selected_action,
            part_type=gauge.selected_part,
            target_id=target_id,
            target_part=target_part
        )

        # 攻撃の場合は事前に計算を実行
        if gauge.selected_action == ActionType.ATTACK:
            # 戦闘計算用のパラメータを収集
            combat_result = self._calculate_combat(actor_eid, gauge.selected_part, target_id, target_part)
            event.calculation_result = combat_result

        self.world.add_component(event_eid, event)

        # 3. フェーズ遷移
        next_p = behavior.get_initial_phase()
        timer = BattleTiming.TARGET_INDICATION if next_p == BattlePhase.TARGET_INDICATION else 0.0

        self._apply_transition(PhaseTransition(
            next_phase=next_p,
            timer=timer,
            actor_id=actor_eid,
            event_id=event_eid
        ))

        self._remove_from_queue(actor_eid)

    def _calculate_combat(
        self,
        actor_eid: int,
        attacker_part_type: str,
        target_id: int,
        target_desired_part: Optional[str]
    ):
        """戦闘計算を実行する"""
        # 1. パラメータ収集
        world = self.world
        a_comps = world.try_get_entity(actor_eid)
        t_comps = world.try_get_entity(target_id)
        
        if not a_comps or not t_comps:
            return None
            
        # 攻撃側メダル
        attacker_medal = MedalParams(attribute=a_comps['medal'].attribute)
        
        # 攻撃パーツ
        part_id = a_comps['partlist'].parts.get(attacker_part_type)
        if not part_id: return None
        p_comps = world.try_get_entity(part_id)
        if not p_comps or 'attack' not in p_comps: return None
        
        attacker_part = AttackParams(
            success=p_comps['attack'].success,
            attack=p_comps['attack'].attack,
            part_attribute=p_comps['part'].attribute,
            skill_type=p_comps['attack'].skill_type,
            trait=p_comps['attack'].trait
        )
        
        # 攻撃側脚部
        attacker_legs = self._get_legs_stats(actor_eid)
        
        # 防御側メダル
        target_medal = MedalParams(attribute=t_comps['medal'].attribute)
        
        # 防御側脚部
        target_legs = self._get_legs_stats(target_id)
        
        # 防御側ゲージペナルティ情報
        t_gauge = t_comps.get('gauge')
        t_status = t_gauge.status if t_gauge else ""
        t_sel_part = t_gauge.selected_part if t_gauge else None
        t_skill_type = None
        if t_sel_part:
            tp_id = t_comps['partlist'].parts.get(t_sel_part)
            if tp_id:
                tp_comps = world.try_get_entity(tp_id)
                if tp_comps and 'attack' in tp_comps:
                    t_skill_type = tp_comps['attack'].skill_type

        # 生存パーツ HP
        target_part_hps = self._get_alive_parts_hp(target_id)

        # 2. 戦闘計算実行
        stats = calculate_adjusted_stats(
            attacker_medal=attacker_medal,
            attacker_part=attacker_part,
            attacker_legs=attacker_legs,
            target_medal=target_medal,
            target_legs=target_legs
        )
        
        penalty = get_defensive_penalty(
            target_gauge_status=t_status,
            target_selected_part=t_sel_part,
            target_part_skill_type=t_skill_type
        )
        
        return calculate_combat_result(
            stats=stats,
            penalty=penalty,
            trait_name=attacker_part.trait,
            target_part_hps=target_part_hps,
            target_desired_part=target_desired_part
        )

    # --- Local Helpers (Refactoring candidate for flow_handler) ---

    def _remove_from_queue(self, eid: int):
        if self.context and eid in self.context.waiting_queue:
            self.context.waiting_queue.remove(eid)

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

    def _get_legs_stats(self, eid: int) -> LegsStats:
        comps = self.world.try_get_entity(eid)
        if comps and 'partlist' in comps:
            legs_id = comps['partlist'].parts.get(PartType.LEGS)
            if legs_id:
                l_comps = self.world.try_get_entity(legs_id)
                if l_comps and 'mobility' in l_comps:
                    return LegsStats(mobility=l_comps['mobility'].mobility, defense=l_comps['mobility'].defense)
        return LegsStats(0, 0)

    def _get_alive_parts_hp(self, eid: int) -> Dict[str, int]:
        comps = self.world.try_get_entity(eid)
        if not comps or 'partlist' not in comps: return {}
        res = {}
        for pt, pid in comps['partlist'].parts.items():
            p_comps = self.world.try_get_entity(pid)
            if p_comps and 'health' in p_comps:
                hp = p_comps['health'].hp
                if hp > 0: res[pt] = hp
        return res

    def _apply_gauge_reset(self, gauge, reset_data):
        gauge.status = reset_data.status
        gauge.progress = reset_data.progress
        if reset_data.clear_selection:
            gauge.selected_action = None
            gauge.selected_part = None
            gauge.part_targets = {}

