"""
ECS から Snapshot への変換ロジック（ビルダー群）
"""

from typing import Dict, Any, List, Optional, Tuple
import pygame
from ui.config import UI_PARAMS, COLORS, PART_LABELS, MENU_PART_ORDER
from battle.constants import BattlePhase, BattleTiming
from domain.constants import GaugeStatus, TeamType, PartType
from domain.gauge_logic import calculate_gauge_ratio
from domain.skill_logic import get_skill_behavior
from .animation_logic import CutinAnimationLogic
from .ui_hit_tester import UIHitTester
from .snapshot import (
    CharacterViewData, LogWindowData,
    ActionMenuData, ActionButtonData, GameOverData, CutinStateData
)

class FieldSnapshotBuilder:
    """フィールド表示用データの構築を担当"""
    def __init__(self, world):
        self.world = world

    def build_characters(self, context, flow) -> Dict[int, CharacterViewData]:
        chars = {}
        # 画面サイズはレンダリング時に解決するため、ここでは相対座標 (PositionComponent) をそのまま渡す
        for eid, comps in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'medal'):
            g, team = comps['gauge'], comps['team']
            pos = comps['position']

            # アイコンの X 座標（相対値）計算
            icon_x_ratio = self._calc_icon_x_ratio(pos.x, g, team.team_type)

            # ホーム位置 X（相対値）
            gauge_w_ratio = UI_PARAMS['GAUGE_WIDTH_RATIO']
            home_x_ratio = pos.x + (gauge_w_ratio if team.team_type == TeamType.ENEMY else 0)

            v_info = self.get_visual_info(comps)

            # 停止状態（サンダー等）の判定
            # 頭部が健在（機能停止していない）かつ、stop状態がある場合のみ表示対象とする
            is_head_alive = v_info['is_alive_map'].get(PartType.HEAD, True)
            is_stopped = is_head_alive and any(e.type_id == "stop" for e in g.active_effects)

            chars[eid] = CharacterViewData(
                entity_id=eid,
                x_ratio=pos.x,
                y_ratio=pos.y,
                icon_x_ratio=icon_x_ratio,
                home_x_ratio=home_x_ratio,
                home_y_ratio=pos.y,
                team_color=team.team_color,
                name=comps['medal'].nickname,
                border_color=self._get_border_color(eid, g, flow, context),
                part_status=v_info['is_alive_map'],
                is_stopped=is_stopped
            )
        return chars

    def _calc_icon_x_ratio(self, base_x_ratio, gauge, team_type) -> float:
        """ゲージ進捗に応じたアイコンの X 座標（相対値）を計算"""
        center_x_ratio = 0.5
        offset_ratio = 0.05 # 中央からのオフセット
        ratio = calculate_gauge_ratio(gauge.status, gauge.progress)

        if team_type == TeamType.PLAYER:
            # 左 (base) から中央手前へ
            end_x = center_x_ratio - offset_ratio
            return base_x_ratio + ratio * (end_x - base_x_ratio)
        else:
            # 右 (start) から中央奥へ
            gauge_w_ratio = UI_PARAMS['GAUGE_WIDTH_RATIO']
            start_x = base_x_ratio + gauge_w_ratio
            end_x = center_x_ratio + offset_ratio
            return start_x + ratio * (end_x - start_x)

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
        # ターゲット演出中、またはその後のカットイン演出中も表示を維持する
        display_phases = [
            BattlePhase.TARGET_INDICATION,
            BattlePhase.ATTACK_DECLARATION,
            BattlePhase.CUTIN,
            BattlePhase.CUTIN_RESULT
        ]
        if flow.current_phase not in display_phases: return None

        event = self.world.get_component(flow.processing_event_id, 'actionevent')
        if event and event.attacker_id in characters and event.current_target_id in characters:
            # ターゲット指示フェーズ以外ではアニメーションを一時停止（固定のタイムオフセットを返す）
            if flow.current_phase == BattlePhase.TARGET_INDICATION:
                time_offset = max(0, BattleTiming.TARGET_INDICATION - flow.phase_timer)
            else:
                time_offset = BattleTiming.TARGET_INDICATION

            return (characters[event.attacker_id], characters[event.current_target_id], time_offset)
        return None


class UISnapshotBuilder:
    """UI パネルデータの構築を担当"""
    def __init__(self, world):
        self.world = world

    def build_log_window(self, context, flow) -> LogWindowData:
        show_guide = flow.current_phase in [
            BattlePhase.LOG_WAIT, 
            BattlePhase.ATTACK_DECLARATION, 
            BattlePhase.CUTIN_RESULT,
            BattlePhase.OPENING_LOG
        ]
        is_cutin = flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT]
        logs = [] if is_cutin else context.battle_log[-UI_PARAMS['LOG_DISPLAY_LINES']:]
        return LogWindowData(logs=logs, show_input_guidance=show_guide, is_active=True)

    def build_action_menu(self, context, flow, screen_size: Tuple[int, int]) -> ActionMenuData:
        """
        アクションメニューの Snapshot を生成する。
        レイアウト計算（Rect）もここで行う。
        """
        if flow.current_phase != BattlePhase.INPUT:
            return ActionMenuData(is_active=False)
        
        comps = self.world.try_get_components(context.current_turn_entity_id, 'medal', 'partlist')
        if not comps:
            return ActionMenuData(is_active=False)

        buttons = []
        for p_type in MENU_PART_ORDER:
            p_id = comps['partlist'].parts.get(p_type)
            p_data = self.world.try_get_entity(p_id)
            if p_data:
                # get_skill_behavior からスキル名を取得
                skill_name = ""
                if 'attack' in p_data:
                    skill_type = p_data['attack'].skill_type
                    skill_name = get_skill_behavior(skill_type).name

                buttons.append(ActionButtonData(
                    label=p_data['name'].name,
                    enabled=p_data['health'].hp > 0,
                    skill_label=skill_name
                ))
        buttons.append(ActionButtonData(label="スキップ", enabled=True, skill_label="なし"))

        # レイアウト計算
        layouts = UIHitTester.calculate_action_menu_layout(len(buttons), screen_size)

        return ActionMenuData(
            actor_name=comps['medal'].nickname,
            buttons=buttons,
            selected_index=context.selected_menu_index,
            is_active=True,
            button_rects=layouts
        )

    def build_game_over(self, flow) -> GameOverData:
        return GameOverData(winner=flow.winner or "", is_active=(flow.current_phase == BattlePhase.GAME_OVER))


class CutinSnapshotBuilder:
    """カットイン演出用データの構築を担当"""
    def __init__(self, world, field_builder: FieldSnapshotBuilder):
        self.world = world
        self.field_builder = field_builder

    def build(self, flow, screen_size) -> CutinStateData:
        """
        Snapshot 生成時に画面サイズを受け取り、Logic に渡す。
        """
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

        # ロジック呼び出し（画面サイズ渡し）
        state = CutinAnimationLogic.calculate_frame(
            progress, trait, atk_comps['team'].team_type == TeamType.ENEMY,
            event.calculation_result, screen_size
        )

        # 表示情報の合成
        atk_v, tgt_v = self.field_builder.get_visual_info(atk_comps), self.field_builder.get_visual_info(tgt_comps, show_hp=True)
        state.attacker.update({'color': atk_v['color'], 'is_alive_map': atk_v['is_alive_map']})
        state.defender.update({'color': tgt_v['color'], 'is_alive_map': tgt_v['is_alive_map'], 'hp_bars': tgt_v['hp_bars']})
        state.bullet['type'] = trait

        return state
