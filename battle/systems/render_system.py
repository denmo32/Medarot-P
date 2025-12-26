"""描画ロジック（データ加工）を担当するシステム"""

from core.ecs import System
from config import COLORS, GAME_PARAMS
from battle.utils import calculate_current_x
from components.battle_flow import BattleFlowComponent

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

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        self.renderer.clear()
        self.renderer.draw_team_titles("プレイヤーチーム", "エネミーチーム")

        char_positions = {}
        for eid, comps in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'defeated', 'medal'):
            if comps['defeated'].is_defeated: continue
            
            pos, gauge, team, medal = comps['position'], comps['gauge'], comps['team'], comps['medal']
            
            # 共通の座標計算ロジックを使用
            icon_x = calculate_current_x(pos.x, gauge.status, gauge.progress, team.team_type)
            
            char_positions[eid] = {'x': pos.x, 'y': pos.y, 'icon_x': icon_x}
            self.renderer.draw_character_info(pos.x, pos.y, medal.nickname, icon_x, team.team_color)

            # HPバー
            hp_data = []
            for p_key, p_color in zip(['head', 'right_arm', 'left_arm', 'legs'], 
                                     [COLORS['HP_HEAD'], COLORS['HP_RIGHT_ARM'], COLORS['HP_LEFT_ARM'], COLORS['HP_LEG']]):
                p_id = comps['partlist'].parts.get(p_key)
                if p_id:
                    h = self.world.entities[p_id]['health']
                    hp_data.append({'ratio': h.hp / h.max_hp, 'color': p_color})
            self.renderer.draw_hp_bars(pos.x, pos.y, hp_data)

        # ターゲット表示
        target_eid = None
        if flow.current_phase == BattleFlowComponent.PHASE_INPUT:
            eid = context.current_turn_entity_id
            if eid in self.world.entities and context.selected_menu_index < 3:
                target_eid = self.world.entities[eid]['gauge'].part_targets.get(["head", "right_arm", "left_arm"][context.selected_menu_index])
        
        # 実行中のイベントターゲット表示
        elif flow.processing_event_id and flow.processing_event_id in self.world.entities:
            event = self.world.entities[flow.processing_event_id].get('actionevent')
            if event:
                target_eid = event.current_target_id
        
        if target_eid:
            self.renderer.draw_target_marker(target_eid, char_positions)

        # ログ待ちは「入力待ち」として表示フラグを立てる
        waiting_for_input = (flow.current_phase == BattleFlowComponent.PHASE_LOG_WAIT)
        self.renderer.draw_message_window(context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:], waiting_for_input)
        
        if flow.current_phase == BattleFlowComponent.PHASE_INPUT:
            self._process_action_menu(context)

        if flow.current_phase == BattleFlowComponent.PHASE_GAME_OVER:
            self.renderer.draw_game_over(flow.winner)
            
        self.renderer.present()

    def _process_action_menu(self, context):
        eid = context.current_turn_entity_id
        comps = self.world.entities[eid]
        buttons = []
        for key in ['head', 'right_arm', 'left_arm']:
            p_id = comps['partlist'].parts.get(key)
            p_comps = self.world.entities[p_id]
            buttons.append({'label': p_comps['name'].name, 'enabled': p_comps['health'].hp > 0})
        buttons.append({'label': "スキップ", 'enabled': True})
        self.renderer.draw_action_menu(comps['medal'].nickname, buttons, context.selected_menu_index)