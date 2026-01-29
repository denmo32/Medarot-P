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
        if not context or not flow:
            return BattleStateSnapshot()

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
        """全機体のフィールド表示データを生成"""
        chars = {}
        for eid, comps in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'medal'):
            g, team = comps['gauge'], comps['team']
            
            # アイコンの位置計算（ゲージ連動）
            icon_x = self._calculate_current_icon_x(comps['position'].x, g, team.team_type)
            home_x = comps['position'].x + (GAME_PARAMS['GAUGE_WIDTH'] if team.team_type == TeamType.ENEMY else 0)

            # 部位の生存状態マップ取得
            visual_info = self._get_visual_info(comps)

            chars[eid] = CharacterViewData(
                entity_id=eid, 
                x=comps['position'].x, 
                y=comps['position'].y,
                icon_x=icon_x, 
                home_x=home_x, 
                home_y=comps['position'].y,
                team_color=team.team_color, 
                name=comps['medal'].nickname,
                border_color=self._get_border_color(eid, g, flow, context),
                part_status=visual_info['is_alive_map']
            )
        return chars

    def _calculate_current_icon_x(self, base_x: int, gauge, team_type: str) -> float:
        """ゲージの進捗に応じてアイコンのX座標を計算"""
        center_x, offset = GAME_PARAMS['SCREEN_WIDTH'] // 2, 40
        ratio = calculate_gauge_ratio(gauge.status, gauge.progress)
        
        if team_type == TeamType.PLAYER:
            # プレイヤー：左(base_x) -> 中央手前(offset)
            return base_x + ratio * ((center_x - offset) - base_x)
        else:
            # エネミー：右(base_x + width) -> 中央手前(offset)
            start_x = base_x + GAME_PARAMS['GAUGE_WIDTH']
            return start_x + ratio * ((center_x + offset) - start_x)

    def _get_border_color(self, eid, gauge, flow, context) -> Optional[tuple]:
        """機体の現在のステータスに応じた強調枠の色を決定"""
        if eid == flow.active_actor_id or eid in context.waiting_queue or gauge.status == GaugeStatus.ACTION_CHOICE:
            return COLORS.get('BORDER_WAIT')
        if gauge.status == GaugeStatus.CHARGING:
            return COLORS.get('BORDER_CHARGE')
        if gauge.status == GaugeStatus.COOLDOWN:
            return COLORS.get('BORDER_COOLDOWN')
        return None

    def _get_visual_info(self, comps, show_hp: bool = False) -> Dict[str, Any]:
        """パーツの生存状態とHPバー情報を抽出する共通メソッド"""
        hp_bars = []
        is_alive_map = {}
        part_list = comps['partlist']
        
        for p_key in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]:
            p_id = part_list.parts.get(p_key)
            p_comps = self.world.try_get_entity(p_id)
            if p_comps and 'health' in p_comps:
                h = p_comps['health']
                is_alive = h.hp > 0
                is_alive_map[p_key] = is_alive
                
                if show_hp:
                    hp_bars.append({
                        'key': p_key, 
                        'label': PART_LABELS.get(p_key, ""), 
                        'current': int(h.display_hp),
                        'max': h.max_hp, 
                        'ratio': h.display_hp / h.max_hp if h.max_hp > 0 else 0
                    })
        
        return {
            'color': comps['team'].team_color, 
            'is_alive_map': is_alive_map,
            'hp_bars': hp_bars if show_hp else None
        }

    def _get_active_target_eid(self, context, flow) -> Optional[int]:
        """入力メニューで現在フォーカスしている攻撃のターゲット先を取得"""
        if flow.current_phase != BattlePhase.INPUT:
            return None
            
        eid = context.current_turn_entity_id
        gauge = self.world.get_component(eid, 'gauge')
        if not gauge:
            return None
        
        idx = context.selected_menu_index
        if idx < len(MENU_PART_ORDER):
            p_type = MENU_PART_ORDER[idx]
            target_data = gauge.part_targets.get(p_type)
            if target_data:
                return target_data[0]
        return None

    def _build_target_line(self, characters, flow):
        """ターゲット指示演出用のライン情報を構築"""
        if flow.current_phase != BattlePhase.TARGET_INDICATION:
            return None
        
        event_comps = self.world.try_get_entity(flow.processing_event_id)
        if not event_comps or 'actionevent' not in event_comps:
            return None
        
        event = event_comps['actionevent']
        atk_id, tgt_id = event.attacker_id, event.current_target_id
        
        if atk_id in characters and tgt_id in characters:
            elapsed = max(0, BattleTiming.TARGET_INDICATION - flow.phase_timer)
            return (characters[atk_id], characters[tgt_id], elapsed)
        return None

    def _build_log_window(self, context, flow) -> LogWindowData:
        """ログウィンドウの状態を構築"""
        show_guide = flow.current_phase in [BattlePhase.LOG_WAIT, BattlePhase.ATTACK_DECLARATION, BattlePhase.CUTIN_RESULT]
        # カットイン演出中はメインログを非表示にする
        is_cutin_active = flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT]
        
        logs = [] if is_cutin_active else context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:]
        return LogWindowData(logs=logs, show_input_guidance=show_guide, is_active=True)

    def _build_action_menu(self, context, flow) -> ActionMenuData:
        """プレイヤー入力用のアクションメニュー情報を構築"""
        if flow.current_phase != BattlePhase.INPUT:
            return ActionMenuData(is_active=False)
        
        eid = context.current_turn_entity_id
        comps = self.get_comps(eid, 'medal', 'partlist')
        if not comps:
            return ActionMenuData(is_active=False)

        buttons = []
        for p_type in MENU_PART_ORDER:
            p_id = comps['partlist'].parts.get(p_type)
            p_data = self.world.try_get_entity(p_id)
            if p_data:
                buttons.append(ActionButtonData(label=p_data['name'].name, enabled=p_data['health'].hp > 0))
        
        buttons.append(ActionButtonData(label="スキップ", enabled=True))
        
        return ActionMenuData(
            actor_name=comps['medal'].nickname, 
            buttons=buttons, 
            selected_index=context.selected_menu_index, 
            is_active=True
        )

    def _build_game_over(self, flow) -> GameOverData:
        """勝敗表示情報の構築"""
        return GameOverData(winner=flow.winner or "", is_active=(flow.current_phase == BattlePhase.GAME_OVER))

    def _build_cutin_state(self, flow) -> CutinStateData:
        """カットイン演出の詳細情報を構築"""
        event_comps = self.world.try_get_entity(flow.processing_event_id)
        if not event_comps:
            return CutinStateData(False)
        
        event = event_comps['actionevent']
        atk_comps = self.world.try_get_entity(event.attacker_id)
        tgt_comps = self.world.try_get_entity(event.current_target_id)
        if not atk_comps or not tgt_comps:
            return CutinStateData(False)

        # 攻撃パーツの特性（演出の分岐用）
        trait = "normal"
        atk_part_id = atk_comps['partlist'].parts.get(event.part_type)
        atk_part_comps = self.world.try_get_entity(atk_part_id)
        if atk_part_comps and 'attack' in atk_part_comps:
            trait = atk_part_comps['attack'].trait

        progress = flow.cutin_progress if flow.current_phase == BattlePhase.CUTIN else 1.0
        is_enemy = (atk_comps['team'].team_type == TeamType.ENEMY)
        
        # 演出用アニメーション座標の計算をAnimationLogicに委譲
        state = CutinAnimationLogic.calculate_frame(progress, trait, is_enemy, event.calculation_result)
        
        # 表示に必要なエンティティ情報をSnaphost用に追加
        atk_visual = self._get_visual_info(atk_comps, show_hp=False)
        tgt_visual = self._get_visual_info(tgt_comps, show_hp=True)
        
        state.attacker.update({
            'color': atk_visual['color'], 
            'is_alive_map': atk_visual['is_alive_map']
        })
        state.defender.update({
            'color': tgt_visual['color'], 
            'is_alive_map': tgt_visual['is_alive_map'],
            'hp_bars': tgt_visual['hp_bars']
        })
        state.bullet['type'] = trait
        
        return state

    def get_comps(self, eid, *names):
        """ヘルパー: 指定したコンポーネントをすべて持つエンティティの情報を取得"""
        return self.world.try_get_components(eid, *names)