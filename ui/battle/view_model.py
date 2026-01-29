"""ECSからSnapshotへの変換ロジック（ViewModel）"""

from typing import Dict, Any, List, Optional
from config import GAME_PARAMS, COLORS
from battle.constants import BattlePhase, BattleTiming, PART_LABELS, MENU_PART_ORDER
from domain.constants import GaugeStatus, TeamType, PartType
from domain.gauge_logic import calculate_gauge_ratio
from battle.mechanics.targeting import TargetingMechanics
from battle.mechanics.flow import get_battle_state
from .animation_logic import CutinAnimationLogic
from .snapshot import (
    BattleStateSnapshot, CharacterViewData, LogWindowData, 
    ActionMenuData, ActionButtonData, GameOverData, CutinStateData
)

class BattleViewModel:
    """Worldの状態を解析し、描画用の不変なデータ（Snapshot）に変換する"""
    
    def __init__(self, world):
        self.world = world

    def create_snapshot(self) -> BattleStateSnapshot:
        """現在の世界の状態を切り出し、Snapshotを生成する"""
        context, flow = get_battle_state(self.world)
        if not context or not flow: return BattleStateSnapshot()

        snapshot = BattleStateSnapshot()
        
        # 1. 各パネル/レイヤーの状態構築
        snapshot.characters = self._build_character_data(context, flow)
        snapshot.target_marker_eid = self._get_active_target_eid(context, flow)
        snapshot.target_line = self._build_target_line(snapshot.characters, flow)
        snapshot.log_window = self._build_log_window(context, flow)
        snapshot.action_menu = self._build_action_menu(context, flow)
        snapshot.game_over = self._build_game_over(flow)

        # 2. カットイン演出（進行度に応じた計算はAnimationLogicに委譲）
        if flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT]:
            snapshot.cutin = self._build_cutin_state(flow)
        
        return snapshot

    def _build_character_data(self, context, flow) -> Dict[int, CharacterViewData]:
        chars = {}
        for eid, comps in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'medal'):
            g, team = comps['gauge'], comps['team']
            icon_x = self._calculate_current_icon_x(comps['position'].x, g, team.team_type)
            home_x = comps['position'].x + (GAME_PARAMS['GAUGE_WIDTH'] if team.team_type == TeamType.ENEMY else 0)

            chars[eid] = CharacterViewData(
                entity_id=eid, x=comps['position'].x, y=comps['position'].y,
                icon_x=icon_x, home_x=home_x, home_y=comps['position'].y,
                team_color=team.team_color, name=comps['medal'].nickname,
                border_color=self._get_border_color(eid, g, flow, context),
                part_status=self._get_part_status_map(comps['partlist'])
            )
        return chars

    def _calculate_current_icon_x(self, base_x: int, gauge, team_type: str) -> float:
        center_x, offset = GAME_PARAMS['SCREEN_WIDTH'] // 2, 40
        ratio = calculate_gauge_ratio(gauge.status, gauge.progress)
        
        if team_type == TeamType.PLAYER:
            return base_x + ratio * ((center_x - offset) - base_x)
        else:
            start_x = base_x + GAME_PARAMS['GAUGE_WIDTH']
            return start_x + ratio * ((center_x + offset) - start_x)

    def _get_border_color(self, eid, gauge, flow, context):
        if eid == flow.active_actor_id or eid in context.waiting_queue or gauge.status == GaugeStatus.ACTION_CHOICE:
            return COLORS.get('BORDER_WAIT')
        if gauge.status == GaugeStatus.CHARGING: return COLORS.get('BORDER_CHARGE')
        if gauge.status == GaugeStatus.COOLDOWN: return COLORS.get('BORDER_COOLDOWN')
        return None

    def _get_part_status_map(self, part_list_comp) -> Dict[str, bool]:
        status_map = {}
        for pt, pid in part_list_comp.parts.items():
            p_comps = self.world.try_get_entity(pid)
            status_map[pt] = p_comps['health'].hp > 0 if p_comps else False
        return status_map

    def _get_active_target_eid(self, context, flow) -> Optional[int]:
        if flow.current_phase != BattlePhase.INPUT: return None
        eid = context.current_turn_entity_id
        
        comps = self.world.try_get_components(eid, 'gauge')
        if not comps: return None
        
        idx = context.selected_menu_index
        if idx < len(MENU_PART_ORDER):
            p_type = MENU_PART_ORDER[idx]
            target_data = comps['gauge'].part_targets.get(p_type)
            if target_data: return target_data[0]
        return None

    def _build_target_line(self, characters, flow):
        if flow.current_phase != BattlePhase.TARGET_INDICATION: return None
        
        event_comps = self.world.try_get_entity(flow.processing_event_id)
        if not event_comps or 'actionevent' not in event_comps: return None
        
        event = event_comps['actionevent']
        atk_id, tgt_id = event.attacker_id, event.current_target_id
        
        if atk_id in characters and tgt_id in characters:
            elapsed = max(0, BattleTiming.TARGET_INDICATION - flow.phase_timer)
            return (characters[atk_id], characters[tgt_id], elapsed)
        return None

    def _build_log_window(self, context, flow) -> LogWindowData:
        # カットイン中はメインログを表示しない
        show_guide = flow.current_phase in [BattlePhase.LOG_WAIT, BattlePhase.ATTACK_DECLARATION, BattlePhase.CUTIN_RESULT]
        is_cutin = flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT]
        
        logs = [] if is_cutin else context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:]
        return LogWindowData(logs=logs, show_input_guidance=show_guide, is_active=True)

    def _build_action_menu(self, context, flow) -> ActionMenuData:
        if flow.current_phase != BattlePhase.INPUT: return ActionMenuData(is_active=False)
        
        eid = context.current_turn_entity_id
        comps = self.world.try_get_components(eid, 'medal', 'partlist')
        if not comps: return ActionMenuData(is_active=False)

        buttons = []
        for p_type in MENU_PART_ORDER:
            p_id = comps['partlist'].parts.get(p_type)
            p_data = self.world.try_get_entity(p_id)
            if p_data:
                buttons.append(ActionButtonData(label=p_data['name'].name, enabled=p_data['health'].hp > 0))
        buttons.append(ActionButtonData(label="スキップ", enabled=True))
        
        return ActionMenuData(actor_name=comps['medal'].nickname, buttons=buttons, 
                              selected_index=context.selected_menu_index, is_active=True)

    def _build_game_over(self, flow) -> GameOverData:
        return GameOverData(winner=flow.winner or "", is_active=(flow.current_phase == BattlePhase.GAME_OVER))

    def _build_cutin_state(self, flow) -> CutinStateData:
        event_comps = self.world.try_get_entity(flow.processing_event_id)
        if not event_comps: return CutinStateData(False)
        
        event = event_comps['actionevent']
        atk_comps = self.world.try_get_entity(event.attacker_id)
        tgt_comps = self.world.try_get_entity(event.current_target_id)
        if not atk_comps or not tgt_comps: return CutinStateData(False)

        # 攻撃パーツの特性を取得
        trait = "normal"
        p_id = atk_comps['partlist'].parts.get(event.part_type)
        p_comps = self.world.try_get_entity(p_id)
        if p_comps and 'attack' in p_comps:
            trait = p_comps['attack'].trait

        progress = flow.cutin_progress if flow.current_phase == BattlePhase.CUTIN else 1.0
        is_enemy = (atk_comps['team'].team_type == TeamType.ENEMY)
        
        # UI座標・演出フェーズの解決
        state = CutinAnimationLogic.calculate_frame(progress, trait, is_enemy, event.calculation_result)
        
        # 表示に必要なエンティティ情報をマージ
        state.attacker.update(self._create_char_visual_info(atk_comps, show_hp=False))
        state.defender.update(self._create_char_visual_info(tgt_comps, show_hp=True))
        state.bullet['type'] = trait
        
        return state

    def _create_char_visual_info(self, comps, show_hp: bool) -> Dict[str, Any]:
        hp_bars = []
        part_list = comps['partlist']
        for p_key in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]:
            p_id = part_list.parts.get(p_key)
            p_comps = self.world.try_get_entity(p_id)
            if p_comps and 'health' in p_comps:
                h = p_comps['health']
                hp_bars.append({
                    'key': p_key, 
                    'label': PART_LABELS.get(p_key, ""), 
                    'current': int(h.display_hp),
                    'max': h.max_hp, 
                    'ratio': h.display_hp / h.max_hp if h.max_hp > 0 else 0
                })
        
        return {
            'color': comps['team'].team_color, 
            'is_alive_map': {it['key']: (it['current'] > 0) for it in hp_bars},
            'hp_bars': hp_bars if show_hp else None
        }