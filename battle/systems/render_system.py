"""描画ロジック（データ加工）を担当するシステム"""

from core.ecs import System
from config import COLORS, GAME_PARAMS
from battle.utils import calculate_current_x
from components.battle_flow import BattleFlowComponent
from battle.constants import PartType, GaugeStatus, BattlePhase, TeamType, PART_LABELS

try:
    from data.parts_data_manager import get_parts_manager
    PARTS_MANAGER_AVAILABLE = True
except ImportError:
    PARTS_MANAGER_AVAILABLE = False

class RenderSystem(System):
    """Worldのコンポーネントから描画用データを抽出しRendererへ渡す"""
    
    def __init__(self, world, renderer):
        super().__init__(world)
        self.renderer = renderer
        self.parts_manager = get_parts_manager() if PARTS_MANAGER_AVAILABLE else None
        self.part_order = [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        self.renderer.clear()
        
        # 1. フィールド情報の描画
        self._draw_field_elements()

        # 2. キャラクター情報の描画（座標計算含む）
        char_positions = self._draw_characters(context, flow)

        # 3. ターゲットマーカーの描画
        self._draw_target_marker(context, flow, char_positions)

        # 4. UI（ログ、アクションメニュー、ゲームオーバー）の描画
        self._draw_ui(context, flow)
            
        self.renderer.present()

    def _draw_field_elements(self):
        """ガイドラインなどの背景要素を描画"""
        self.renderer.draw_field_guides()

    def _draw_characters(self, context, flow):
        """全キャラクターの描画を行い、現在の表示座標リストを返す"""
        char_positions = {}
        
        for eid, comps in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'defeated', 'medal'):
            pos, gauge, team, medal = comps['position'], comps['gauge'], comps['team'], comps['medal']
            
            # 現在位置（アイコンX座標）の計算
            icon_x = calculate_current_x(pos.x, gauge.status, gauge.progress, team.team_type)
            char_positions[eid] = {'x': pos.x, 'y': pos.y, 'icon_x': icon_x}
            
            # 初期位置マーカー
            marker_x = pos.x + GAME_PARAMS['GAUGE_WIDTH'] if team.team_type == TeamType.ENEMY else pos.x
            self.renderer.draw_home_marker(marker_x, pos.y)
            
            # 状態に応じた縁取り色
            border_color = self._get_border_color(eid, gauge, context, flow)

            # キャラ情報（名前とアイコン）
            self.renderer.draw_character_info(pos.x, pos.y, medal.nickname, icon_x, team.team_color, border_color)

            # HPバー
            hp_data = self._build_hp_data(comps['partlist'])
            self.renderer.draw_hp_bars(pos.x, pos.y, hp_data)

        return char_positions

    def _get_border_color(self, eid, gauge, context, flow):
        """状態に応じたアイコンの縁取り色を決定"""
        if eid == flow.active_actor_id or eid in context.waiting_queue or gauge.status == GaugeStatus.ACTION_CHOICE:
            return COLORS.get('BORDER_WAIT')
        elif gauge.status == GaugeStatus.CHARGING:
            return COLORS.get('BORDER_CHARGE')
        elif gauge.status == GaugeStatus.COOLDOWN:
            return COLORS.get('BORDER_COOLDOWN')
        return None

    def _build_hp_data(self, part_list_comp):
        """HPバー表示用のデータを構築"""
        hp_data = []
        for p_key in self.part_order:
            p_id = part_list_comp.parts.get(p_key)
            if p_id:
                h = self.world.entities[p_id]['health']
                hp_data.append({
                    'label': PART_LABELS.get(p_key, ""),
                    'current': h.hp,
                    'max': h.max_hp,
                    'ratio': h.hp / h.max_hp if h.max_hp > 0 else 0
                })
        return hp_data

    def _draw_target_marker(self, context, flow, char_positions):
        """現在のターゲットにマーカーを表示"""
        target_eid = None
        
        # 入力フェーズ：選択中のターゲット
        if flow.current_phase == BattlePhase.INPUT:
            eid = context.current_turn_entity_id
            if eid in self.world.entities and context.selected_menu_index < 3:
                # ターゲットデータは (target_id, target_part)
                # selected_menu_index: 0=Head, 1=Right, 2=Left
                target_key = [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM][context.selected_menu_index]
                target_data = self.world.entities[eid]['gauge'].part_targets.get(target_key)
                if target_data:
                    target_eid = target_data[0]
        
        # 実行フェーズ：イベントのターゲット
        elif flow.processing_event_id and flow.processing_event_id in self.world.entities:
            event = self.world.entities[flow.processing_event_id].get('actionevent')
            if event:
                target_eid = event.current_target_id
        
        if target_eid:
            self.renderer.draw_target_marker(target_eid, char_positions)

    def _draw_ui(self, context, flow):
        """ログウィンドウ、アクションメニュー、ゲームオーバー画面の描画"""
        # ログ待ちは「入力待ち」として表示フラグを立てる
        waiting_for_input = (flow.current_phase == BattlePhase.LOG_WAIT)
        self.renderer.draw_message_window(context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:], waiting_for_input)
        
        if flow.current_phase == BattlePhase.INPUT:
            self._process_action_menu(context)

        if flow.current_phase == BattlePhase.GAME_OVER:
            self.renderer.draw_game_over(flow.winner)

    def _process_action_menu(self, context):
        """アクションメニューの内容を構築して描画"""
        eid = context.current_turn_entity_id
        comps = self.world.entities[eid]
        buttons = []
        
        # 各パーツボタン
        for key in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]:
            p_id = comps['partlist'].parts.get(key)
            p_comps = self.world.entities[p_id]
            buttons.append({'label': p_comps['name'].name, 'enabled': p_comps['health'].hp > 0})
        
        # スキップボタン
        buttons.append({'label': "スキップ", 'enabled': True})
        
        self.renderer.draw_action_menu(comps['medal'].nickname, buttons, context.selected_menu_index)