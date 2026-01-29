"""ECSからSnapshotへの変換ロジック（ViewModel）"""

from typing import Dict, Any, List, Optional
from config import GAME_PARAMS, COLORS
from battle.constants import BattlePhase, BattleTiming, PART_LABELS, MENU_PART_ORDER
from domain.constants import GaugeStatus, TeamType, PartType
from domain.gauge_logic import calculate_gauge_ratio
from battle.mechanics.flow import get_battle_state
from .animation_logic import CutinAnimationLogic
from .layout_utils import calculate_action_menu_layout
from .snapshot import (
    BattleStateSnapshot, CharacterViewData, LogWindowData, 
    ActionMenuData, ActionButtonData, GameOverData, CutinStateData
)

class BattleViewModel:
    """Worldの状態を解析し、描画用のSnapshotに変換する"""
    
    def __init__(self, world):
        self.world = world
        self.field_builder = FieldSnapshotBuilder(world)
        self.ui_builder = UISnapshotBuilder(world)
        self.cutin_builder = CutinSnapshotBuilder(world, self.field_builder)

    def create_snapshot(self) -> BattleStateSnapshot:
        """現在の世界の状態を切り出し、Snapshotを生成する"""
        context, flow = get_battle_state(self.world)
        if not context or not flow:
            return BattleStateSnapshot()

        snapshot = BattleStateSnapshot()
        
        # 1. 各レイヤーの構築をビルダーに委譲
        snapshot.characters = self.field_builder.build_characters(context, flow)
        snapshot.target_marker_eid = self.field_builder.get_active_target_eid(context, flow)
        snapshot.target_line = self.field_builder.build_target_line(snapshot.characters, flow)
        
        snapshot.log_window = self.ui_builder.build_log_window(context, flow)
        snapshot.action_menu = self.ui_builder.build_action_menu(context, flow)
        snapshot.game_over = self.ui_builder.build_game_over(flow)

        # 2. カットイン演出
        if flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT]:
            snapshot.cutin = self.cutin_builder.build(flow)
        
        return snapshot

    def hit_test_action_menu(self, mx: int, my: int) -> Optional[int]:
        """マウス座標がどのボタンにあるかを判定"""
        _, flow = get_battle_state(self.world)
        if not flow or flow.current_phase != BattlePhase.INPUT:
            return None

        layout = calculate_action_menu_layout(len(MENU_PART_ORDER) + 1)
        for i, rect in enumerate(layout):
            if rect.collidepoint(mx, my):
                return i
        return None


class FieldSnapshotBuilder:
    """フィールド表示用データの構築を担当"""
    def __init__(self, world):
        self.world = world

    def build_characters(self, context, flow) -> Dict[int, CharacterViewData]:
        chars = {}
        for eid, comps in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'medal'):
            g, team = comps['gauge'], comps['team']
            
            # アイコン座標計算
            icon_x = self._calc_icon_x(comps['position'].x, g, team.team_type)
            home_x = comps['position'].x + (GAME_PARAMS['GAUGE_WIDTH'] if team.team_type == TeamType.ENEMY else 0)
            
            # ビジュアル情報
            v_info = self.get_visual_info(comps)

            chars[eid] = CharacterViewData(
                entity_id=eid, x=comps['position'].x, y=comps['position'].y,
                icon_x=icon_x, home_x=home_x, home_y=comps['position'].y,
                team_color=team.team_color, name=comps['medal'].nickname,
                border_color=self._get_border_color(eid, g, flow, context),
                part_status=v_info['is_alive_map']
            )
        return chars

    def _calc_icon_x(self, base_x, gauge, team_type) -> float:
        center_x, offset = GAME_PARAMS['SCREEN_WIDTH'] // 2, 40
        ratio = calculate_gauge_ratio(gauge.status, gauge.progress)
        if team_type == TeamType.PLAYER:
            return base_x + ratio * ((center_x - offset) - base_x)
        else:
            start_x = base_x + GAME_PARAMS['GAUGE_WIDTH']
            return start_x + ratio * ((center_x + offset) - start_x)

    def _get_border_color(self, eid, gauge, flow, context) -> Optional[tuple]:
        if eid == flow.active_actor_id or eid in context.waiting_queue or gauge.status == GaugeStatus.ACTION_CHOICE:
            return COLORS.get('BORDER_WAIT')
        if gauge.status == GaugeStatus.CHARGING:
            return COLORS.get('BORDER_CHARGE')
        if gauge.status == GaugeStatus.COOLDOWN:
            return COLORS.get('BORDER_COOLDOWN')
        return None

    def get_visual_info(self, comps, show_hp: bool = False) -> Dict[str, Any]:
        hp_bars, is_alive_map = [], {}
        part_list = comps['partlist']
        for p_key in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]:
            p_id = part_list.parts.get(p_key)
            p_data = self.world.try_get_entity(p_id)
            if p_data and 'health' in p_data:
                h = p_data['health']
                is_alive_map[p_key] = (h.hp > 0)
                if show_hp:
                    hp_bars.append({
                        'key': p_key, 'label': PART_LABELS.get(p_key, ""), 
                        'current': int(h.display_hp), 'max': h.max_hp, 
                        'ratio': h.display_hp / h.max_hp if h.max_hp > 0 else 0
                    })
        return {'color': comps['team'].team_color, 'is_alive_map': is_alive_map, 'hp_bars': hp_bars if show_hp else None}

    def get_active_target_eid(self, context, flow) -> Optional[int]:
        if flow.current_phase != BattlePhase.INPUT: return None
        gauge = self.world.get_component(context.current_turn_entity_id, 'gauge')
        if not gauge or context.selected_menu_index >= len(MENU_PART_ORDER): return None
        target_data = gauge.part_targets.get(MENU_PART_ORDER[context.selected_menu_index])
        return target_data[0] if target_data else None

    def build_target_line(self, characters, flow):
        if flow.current_phase != BattlePhase.TARGET_INDICATION: return None
        event = self.world.get_component(flow.processing_event_id, 'actionevent')
        if event and event.attacker_id in characters and event.current_target_id in characters:
            return (characters[event.attacker_id], characters[event.current_target_id], max(0, BattleTiming.TARGET_INDICATION - flow.phase_timer))
        return None


class UISnapshotBuilder:
    """UIパネルデータの構築を担当"""
    def __init__(self, world):
        self.world = world

    def build_log_window(self, context, flow) -> LogWindowData:
        show_guide = flow.current_phase in [BattlePhase.LOG_WAIT, BattlePhase.ATTACK_DECLARATION, BattlePhase.CUTIN_RESULT]
        is_cutin = flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT]
        logs = [] if is_cutin else context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:]
        return LogWindowData(logs=logs, show_input_guidance=show_guide, is_active=True)

    def build_action_menu(self, context, flow) -> ActionMenuData:
        if flow.current_phase != BattlePhase.INPUT: return ActionMenuData(is_active=False)
        comps = self.world.try_get_components(context.current_turn_entity_id, 'medal', 'partlist')
        if not comps: return ActionMenuData(is_active=False)

        buttons = []
        for p_type in MENU_PART_ORDER:
            p_id = comps['partlist'].parts.get(p_type)
            p_data = self.world.try_get_entity(p_id)
            if p_data:
                buttons.append(ActionButtonData(label=p_data['name'].name, enabled=p_data['health'].hp > 0))
        buttons.append(ActionButtonData(label="スキップ", enabled=True))
        
        return ActionMenuData(actor_name=comps['medal'].nickname, buttons=buttons, selected_index=context.selected_menu_index, is_active=True)

    def build_game_over(self, flow) -> GameOverData:
        return GameOverData(winner=flow.winner or "", is_active=(flow.current_phase == BattlePhase.GAME_OVER))


class CutinSnapshotBuilder:
    """カットイン演出用データの構築を担当"""
    def __init__(self, world, field_builder: FieldSnapshotBuilder):
        self.world = world
        self.field_builder = field_builder

    def build(self, flow) -> CutinStateData:
        event = self.world.get_component(flow.processing_event_id, 'actionevent')
        atk_comps = self.world.try_get_entity(event.attacker_id) if event else None
        tgt_comps = self.world.try_get_entity(event.current_target_id) if event else None
        if not atk_comps or not tgt_comps: return CutinStateData(False)

        # 特性取得
        trait = "normal"
        atk_part_comps = self.world.try_get_entity(atk_comps['partlist'].parts.get(event.part_type))
        if atk_part_comps and 'attack' in atk_part_comps:
            trait = atk_part_comps['attack'].trait

        progress = flow.cutin_progress if flow.current_phase == BattlePhase.CUTIN else 1.0
        state = CutinAnimationLogic.calculate_frame(progress, trait, atk_comps['team'].team_type == TeamType.ENEMY, event.calculation_result)
        
        # 表示情報の合成
        atk_v, tgt_v = self.field_builder.get_visual_info(atk_comps), self.field_builder.get_visual_info(tgt_comps, show_hp=True)
        state.attacker.update({'color': atk_v['color'], 'is_alive_map': atk_v['is_alive_map']})
        state.defender.update({'color': tgt_v['color'], 'is_alive_map': tgt_v['is_alive_map'], 'hp_bars': tgt_v['hp_bars']})
        state.bullet['type'] = trait
        
        return state