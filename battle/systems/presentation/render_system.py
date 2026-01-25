"""描画ロジック（データ加工）を担当するシステム"""

from core.ecs import System
from config import GAME_PARAMS, COLORS
from battle.constants import BattlePhase, MENU_PART_ORDER, TeamType
from battle.presentation.view_model import BattleViewModel, CutinViewModel
from ui.cutin_renderer import CutinRenderer

class RenderSystem(System):
    """Worldのコンポーネントから描画用データを抽出しRendererへ渡す"""
    
    def __init__(self, world, field_renderer, ui_renderer):
        super().__init__(world)
        self.field_renderer = field_renderer
        self.ui_renderer = ui_renderer
        self.cutin_renderer = CutinRenderer(field_renderer.screen)

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context, flow = entities[0][1]['battlecontext'], entities[0][1]['battleflow']

        self.field_renderer.clear()
        self.field_renderer.draw_field_guides()
        char_positions = self._render_characters(context, flow)
        self._render_target_marker(context, flow, char_positions)
        self._render_target_indication_line(context, flow, char_positions)
        self._render_ui(context, flow)

        if flow.current_phase == BattlePhase.CUTIN or flow.current_phase == BattlePhase.CUTIN_RESULT:
            self._render_cutin(context, flow)

        self.field_renderer.present()

    def _render_characters(self, context, flow):
        char_positions = {}
        for eid, _ in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'medal'):
            view_data = BattleViewModel.get_character_view_data(self.world, eid, context, flow)
            char_positions[eid] = {'x': view_data['x'], 'y': view_data['y'], 'icon_x': view_data['icon_x']}
            self.field_renderer.draw_home_marker(view_data['home_x'], view_data['home_y'])
            self.field_renderer.draw_character_icon(view_data['icon_x'], view_data['y'], view_data['team_color'], view_data['part_status'], view_data['border_color'])
            self.field_renderer.draw_text(view_data['name'], (view_data['x'] - 20, view_data['y'] - 25), font_type='medium')
        return char_positions

    def _render_target_marker(self, context, flow, char_positions):
        target_eid = None
        if flow.current_phase == BattlePhase.INPUT:
            eid = context.current_turn_entity_id
            if eid and context.selected_menu_index < len(MENU_PART_ORDER):
                target_data = self.world.entities[eid]['gauge'].part_targets.get(MENU_PART_ORDER[context.selected_menu_index])
                if target_data: target_eid = target_data[0]
        if target_eid and target_eid in char_positions:
            self.field_renderer.draw_target_marker(target_eid, char_positions)

    def _render_target_indication_line(self, context, flow, char_positions):
        if flow.current_phase not in [BattlePhase.TARGET_INDICATION, BattlePhase.ATTACK_DECLARATION, BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT]: return
        event_eid = flow.processing_event_id
        if event_eid is None: return
        event_comps = self.world.try_get_entity(event_eid)
        if not event_comps or 'actionevent' not in event_comps: return
        event = event_comps['actionevent']
        if event.attacker_id in char_positions and event.current_target_id in char_positions:
            start_pos, end_pos = char_positions[event.attacker_id], char_positions[event.current_target_id]
            self.field_renderer.draw_flow_line((start_pos['icon_x'], start_pos['y'] + 20), (end_pos['icon_x'], end_pos['y'] + 20), flow.target_line_offset)

    def _render_ui(self, context, flow):
        show_input_guidance = flow.current_phase in [BattlePhase.LOG_WAIT, BattlePhase.ATTACK_DECLARATION, BattlePhase.CUTIN_RESULT]
        display_logs = [] if flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT] else context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:]
        self.ui_renderer.draw_message_window(display_logs, show_input_guidance)
        
        if flow.current_phase == BattlePhase.INPUT:
            eid = context.current_turn_entity_id
            if eid:
                comps = self.world.entities[eid]
                buttons = [{'label': self.world.entities[p_id]['name'].name, 'enabled': self.world.entities[p_id]['health'].hp > 0} 
                           for p_id in [comps['partlist'].parts.get(k) for k in MENU_PART_ORDER] if p_id]
                buttons.append({'label': "スキップ", 'enabled': True})
                self.ui_renderer.draw_action_menu(comps['medal'].nickname, buttons, context.selected_menu_index)
        
        if flow.current_phase == BattlePhase.GAME_OVER:
            self.ui_renderer.draw_game_over(flow.winner)

    def _render_cutin(self, context, flow):
        """ViewModelが構築した描画ステートをRendererに渡す"""
        state = CutinViewModel.build_action_state(self.world, flow)
        if not state: return

        self.cutin_renderer.draw(
            state['attacker_visual'], state['target_visual'],
            state['progress'], state['result'], 
            mirror=state['is_enemy'],
            attack_trait=state['trait']
        )