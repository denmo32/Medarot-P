"""描画ロジック（データ加工）を担当するシステム"""

from core.ecs import System
from config import COLORS, GAME_PARAMS
from battle.utils import calculate_current_x
from components.battle_flow import BattleFlowComponent
from battle.constants import PartType, GaugeStatus, BattlePhase, TeamType

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
        # HPバーの表示用ラベルと順序
        self.part_labels = {
            PartType.HEAD: "頭部",
            PartType.RIGHT_ARM: "右腕",
            PartType.LEFT_ARM: "左腕",
            PartType.LEGS: "脚部"
        }
        self.part_order = [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        self.renderer.clear()
        
        # ガイドライン（実行ライン）の描画
        self.renderer.draw_field_guides()

        char_positions = {}
        for eid, comps in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'defeated', 'medal'):
            # 敗北しても表示を残すため、defeatedチェックを削除
            
            pos, gauge, team, medal = comps['position'], comps['gauge'], comps['team'], comps['medal']
            
            # 共通の座標計算ロジックを使用
            icon_x = calculate_current_x(pos.x, gauge.status, gauge.progress, team.team_type)
            
            char_positions[eid] = {'x': pos.x, 'y': pos.y, 'icon_x': icon_x}
            
            # 初期位置マーカー
            # エネミーの場合は右端（基準X + ゲージ幅）がホームポジション
            marker_x = pos.x
            if team.team_type == TeamType.ENEMY:
                marker_x = pos.x + GAME_PARAMS['GAUGE_WIDTH']
            
            self.renderer.draw_home_marker(marker_x, pos.y)
            
            # 縁取り色の決定
            border_color = None
            
            # 白色（実行中、実行待ち、コマンド入力待ち）
            if eid == flow.active_actor_id or eid in context.waiting_queue or gauge.status == GaugeStatus.ACTION_CHOICE:
                border_color = COLORS.get('BORDER_WAIT')
            # オレンジ色（チャージ中）
            elif gauge.status == GaugeStatus.CHARGING:
                border_color = COLORS.get('BORDER_CHARGE')
            # 水色（クールダウン中）
            elif gauge.status == GaugeStatus.COOLDOWN:
                border_color = COLORS.get('BORDER_COOLDOWN')

            # キャラ情報（名前とアイコン）
            self.renderer.draw_character_info(pos.x, pos.y, medal.nickname, icon_x, team.team_color, border_color)

            # HPバーデータの構築
            hp_data = []
            for p_key in self.part_order:
                p_id = comps['partlist'].parts.get(p_key)
                if p_id:
                    h = self.world.entities[p_id]['health']
                    hp_data.append({
                        'label': self.part_labels.get(p_key, ""),
                        'current': h.hp,
                        'max': h.max_hp,
                        'ratio': h.hp / h.max_hp if h.max_hp > 0 else 0
                    })
            self.renderer.draw_hp_bars(pos.x, pos.y, hp_data)

        # ターゲット表示
        target_eid = None
        if flow.current_phase == BattlePhase.INPUT:
            eid = context.current_turn_entity_id
            if eid in self.world.entities and context.selected_menu_index < 3:
                # ターゲットデータは (target_id, target_part) のタプルになっている
                target_data = self.world.entities[eid]['gauge'].part_targets.get([PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM][context.selected_menu_index])
                if target_data:
                    target_eid = target_data[0]
        
        # 実行中のイベントターゲット表示
        elif flow.processing_event_id and flow.processing_event_id in self.world.entities:
            event = self.world.entities[flow.processing_event_id].get('actionevent')
            if event:
                target_eid = event.current_target_id
        
        if target_eid:
            self.renderer.draw_target_marker(target_eid, char_positions)

        # ログ待ちは「入力待ち」として表示フラグを立てる
        waiting_for_input = (flow.current_phase == BattlePhase.LOG_WAIT)
        self.renderer.draw_message_window(context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:], waiting_for_input)
        
        if flow.current_phase == BattlePhase.INPUT:
            self._process_action_menu(context)

        if flow.current_phase == BattlePhase.GAME_OVER:
            self.renderer.draw_game_over(flow.winner)
            
        self.renderer.present()

    def _process_action_menu(self, context):
        eid = context.current_turn_entity_id
        comps = self.world.entities[eid]
        buttons = []
        for key in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]:
            p_id = comps['partlist'].parts.get(key)
            p_comps = self.world.entities[p_id]
            buttons.append({'label': p_comps['name'].name, 'enabled': p_comps['health'].hp > 0})
        buttons.append({'label': "スキップ", 'enabled': True})
        self.renderer.draw_action_menu(comps['medal'].nickname, buttons, context.selected_menu_index)