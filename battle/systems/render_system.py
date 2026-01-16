"""描画ロジック（データ加工）を担当するシステム"""

from core.ecs import System
from config import COLORS, GAME_PARAMS
from battle.utils import calculate_current_x
from components.battle_flow import BattleFlowComponent
from battle.constants import PartType, GaugeStatus, BattlePhase, TeamType, PART_LABELS, MENU_PART_ORDER

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
        # HPバーの表示順序（脚部を含む）
        self.hp_bar_order = [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]

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
        
        # 描画対象エンティティの取得
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
        for p_key in self.hp_bar_order:
            p_id = part_list_comp.parts.get(p_key)
            if p_id is not None:
                p_comps = self.world.try_get_entity(p_id)
                if p_comps and 'health' in p_comps:
                    h = p_comps['health']
                    # 真値 (h.hp) ではなく、アニメーション中の表示値 (h.display_hp) を使用
                    hp_data.append({
                        'label': PART_LABELS.get(p_key, ""),
                        'current': int(h.display_hp),
                        'max': h.max_hp,
                        'ratio': h.display_hp / h.max_hp if h.max_hp > 0 else 0
                    })
        return hp_data

    def _draw_target_marker(self, context, flow, char_positions):
        """現在のターゲットにマーカーを表示"""
        target_eid = None
        
        # 入力フェーズ：選択中のターゲット
        if flow.current_phase == BattlePhase.INPUT:
            eid = context.current_turn_entity_id
            if eid is not None:
                actor_comps = self.world.try_get_entity(eid)
                if actor_comps and context.selected_menu_index < len(MENU_PART_ORDER):
                    # 選択中のパーツに対応するターゲットを取得
                    target_key = MENU_PART_ORDER[context.selected_menu_index]
                    target_data = actor_comps['gauge'].part_targets.get(target_key)
                    if target_data:
                        target_eid = target_data[0]
        
        # 実行フェーズ：イベントのターゲット
        elif flow.processing_event_id is not None:
            event_comps = self.world.try_get_entity(flow.processing_event_id)
            if event_comps and 'actionevent' in event_comps:
                event = event_comps['actionevent']
                target_eid = event.current_target_id
        
        if target_eid is not None:
            self.renderer.draw_target_marker(target_eid, char_positions)

    def _draw_ui(self, context, flow):
        """ログウィンドウ、アクションメニュー、ゲームオーバー画面の描画"""
        waiting_for_input = (flow.current_phase == BattlePhase.LOG_WAIT)
        self.renderer.draw_message_window(context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:], waiting_for_input)
        
        if flow.current_phase == BattlePhase.INPUT:
            self._process_action_menu(context)

        if flow.current_phase == BattlePhase.GAME_OVER:
            self.renderer.draw_game_over(flow.winner)

    def _process_action_menu(self, context):
        """アクションメニューの内容を構築して描画"""
        eid = context.current_turn_entity_id
        if eid is None: return
        
        comps = self.world.try_get_entity(eid)
        if not comps: return

        buttons = []
        
        # 定義された順序でパーツボタンを追加
        for key in MENU_PART_ORDER:
            p_id = comps['partlist'].parts.get(key)
            if p_id is not None:
                p_comps = self.world.try_get_entity(p_id)
                if p_comps:
                    buttons.append({
                        'label': p_comps['name'].name, 
                        'enabled': p_comps['health'].hp > 0
                    })
        
        # スキップボタン
        buttons.append({'label': "スキップ", 'enabled': True})
        
        self.renderer.draw_action_menu(comps['medal'].nickname, buttons, context.selected_menu_index)