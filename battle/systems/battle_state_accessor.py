"""バトル状態へのアクセスと操作を提供するヘルパークラス"""

from typing import Optional, Tuple, Dict, Any, List
from core.ecs import World
from battle.mechanics.flow import get_battle_state, PhaseTransition
from battle.mechanics.action import GaugeResetData
from battle.mechanics.action_behavior import ResolutionResult
from battle.constants import BattlePhase


class BattleStateAccessor:
    """
    BattleContext と BattleFlow へのアクセスを提供する。
    
    責任範囲:
    - バトル状態の取得
    - フェーズ遷移
    - エンティティ削除
    - ゲージ操作
    - 待機列管理
    """

    def __init__(self, world: World):
        self.world = world

    # --- データ取得系メソッド ---

    def try_get_components(self, entity_id: int, *names: str) -> Optional[Dict[str, Any]]:
        """指定エンティティから指定されたコンポーネントを安全に取得"""
        return self.world.try_get_components(entity_id, *names)

    def get_part_entity_id(self, entity_id: int, part_type: str) -> Optional[int]:
        """指定機体の指定部位のエンティティ ID を取得"""
        comps = self.try_get_components(entity_id, 'partlist')
        if not comps:
            return None
        return comps['partlist'].parts.get(part_type)

    def get_part_components(self, entity_id: int, part_type: str, *names: str) -> Optional[Dict[str, Any]]:
        """指定機体の指定部位から指定されたコンポーネントを取得"""
        pid = self.get_part_entity_id(entity_id, part_type)
        if pid is None:
            return None
        return self.try_get_components(pid, *names)

    def is_entity_alive(self, entity_id: int) -> bool:
        """エンティティが生存しているか（敗北フラグが立っていないか）"""
        comps = self.world.try_get_entity(entity_id)
        if not comps:
            return False
        defeated = comps.get('defeated')
        return not defeated.is_defeated if defeated else True

    def is_part_alive(self, entity_id: int, part_type: str) -> bool:
        """指定部位が生存しているか（HP > 0）"""
        p_comps = self.get_part_components(entity_id, part_type, 'health')
        return p_comps and p_comps['health'].hp > 0

    def get_alive_parts_hp(self, entity_id: int) -> Dict[str, int]:
        """生存している部位名とその HP の辞書を取得"""
        comps = self.try_get_components(entity_id, 'partlist')
        if not comps:
            return {}
        
        result = {}
        for pt, pid in comps['partlist'].parts.items():
            p_comps = self.world.try_get_entity(pid)
            if p_comps and 'health' in p_comps:
                hp = p_comps['health'].hp
                if hp > 0:
                    result[pt] = hp
        return result

    def get_team_entities(self, team_type: str, only_alive: bool = True) -> List[int]:
        """指定チームのエンティティ ID リストを取得"""
        result = []
        for eid, comps in self.world.get_entities_with_components('team'):
            if comps['team'].team_type == team_type:
                if not only_alive or self.is_entity_alive(eid):
                    result.append(eid)
        return result

    def get_entities_with_components(self, *names: str) -> List[Tuple[int, Dict[str, Any]]]:
        """指定されたコンポーネントをすべて持つエンティティのリストを取得"""
        return self.world.get_entities_with_components(*names)

    @property
    def context(self) -> Optional[Dict[str, Any]]:
        """BattleContextComponent へのアクセス"""
        ctx, _ = get_battle_state(self.world)
        return ctx

    @property
    def flow(self) -> Optional[Dict[str, Any]]:
        """BattleFlowComponent へのアクセス"""
        _, flow = get_battle_state(self.world)
        return flow

    def change_phase(self, next_phase: str, timer: float = 0.0) -> None:
        """単純なフェーズ遷移"""
        self.apply_phase_transition(PhaseTransition(next_phase=next_phase, timer=timer))

    def apply_phase_transition(self, transition: PhaseTransition) -> None:
        """フェーズ遷移指示を適用"""
        flow = self.flow
        if not flow:
            return

        flow.current_phase = transition.next_phase
        flow.phase_timer = transition.timer

        if transition.actor_id is not None:
            flow.active_actor_id = transition.actor_id
        if transition.event_id is not None:
            flow.processing_event_id = transition.event_id

        if transition.logs:
            if transition.clear_logs:
                self.context.battle_log.clear()
            self.context.battle_log.extend(transition.logs)

        # IDLE への遷移時は自動クリーンアップ
        if transition.next_phase == BattlePhase.IDLE:
            flow.processing_event_id = None
            flow.active_actor_id = None
            flow.cutin_progress = 0.0

    def delete_event(self, event_id: int) -> None:
        """ActionEvent エンティティを削除"""
        flow = self.flow
        if flow and flow.processing_event_id == event_id:
            flow.processing_event_id = None
        self.world.delete_entity(event_id)

    def apply_gauge_reset(self, entity_id: int, reset_data: GaugeResetData) -> None:
        """ゲージリセット指示を適用"""
        comps = self.world.try_get_entity(entity_id)
        if not comps or 'gauge' not in comps:
            return

        gauge = comps['gauge']
        gauge.status = reset_data.status
        gauge.progress = reset_data.progress

        if reset_data.clear_selection:
            gauge.selected_action = None
            gauge.selected_part = None
            gauge.part_targets = {}

    def manage_queue(self, entity_id: int, should_add: bool) -> None:
        """待機列への追加・削除"""
        context = self.context
        if not context:
            return
            
        queue = context.waiting_queue
        if should_add and entity_id not in queue:
            queue.append(entity_id)
        elif not should_add and entity_id in queue:
            queue.remove(entity_id)

    def apply_resolution_result(
        self,
        entity_id: int,
        result: ResolutionResult,
        event_id: Optional[int] = None
    ) -> None:
        """
        アクション解決結果を適用する。
        
        Args:
            entity_id: 結果を適用するエンティティ ID
            result: 解決結果オブジェクト
            event_id: 関連する ActionEvent の ID
        """
        context = self.context
        if not context:
            return

        # 1. ログの追加
        if result.logs:
            context.battle_log.extend(result.logs)

        # 2. ダメージの発生
        if result.damage_result and event_id is not None:
            event_comps = self.world.try_get_entity(event_id)
            if event_comps and 'actionevent' in event_comps:
                target_id = event_comps['actionevent'].current_target_id
                damage_comp = result.damage_result.to_component()
                self.world.add_component(target_id, damage_comp)

        # 3. ゲージのリセット
        if result.gauge_reset:
            self.apply_gauge_reset(entity_id, result.gauge_reset)

        # 4. キューからの削除
        if result.should_remove_from_queue:
            self.manage_queue(entity_id, False)

        # 5. フェーズ遷移
        self.apply_phase_transition(PhaseTransition(
            next_phase=result.next_phase,
            timer=result.phase_timer
        ))
