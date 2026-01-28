"""描画ロジック（データ加工）を担当するシステム"""

from core.ecs import System
from config import GAME_PARAMS
from battle.constants import BattlePhase
from battle.presentation.battle_view_model import BattleViewModel
from battle.presentation.cutin_view_model import CutinViewModel
from ui.cutin_renderer import CutinRenderer
from battle.service.flow_service import get_battle_state

class RenderSystem(System):
    """Worldのコンポーネントから描画用データを抽出しRendererへ渡す"""
    
    def __init__(self, world, field_renderer, ui_renderer):
        super().__init__(world)
        self.field_renderer = field_renderer
        self.ui_renderer = ui_renderer
        self.cutin_renderer = CutinRenderer(field_renderer.screen)

    def update(self, dt: float):
        context, flow = get_battle_state(self.world)
        if not context or not flow: return

        self.field_renderer.clear()
        self.field_renderer.draw_field_guides()
        
        # 1. 機体と基本アイコンの描画
        char_positions = self._render_characters(context, flow)
        
        # 2. 演出用マーカー・ラインの描画
        self._render_target_marker(context, flow, char_positions)
        self._render_target_indication_line(context, flow, char_positions)
        
        # 3. HUD・UIの描画
        self._render_ui(context, flow)

        # 4. カットイン演出
        if flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT]:
            self._render_cutin(context, flow)

        self.field_renderer.present()

    def _render_characters(self, context, flow):
        char_positions = {}
        for eid, _ in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'medal'):
            view_data = BattleViewModel.get_character_view_data(self.world, eid, context, flow)
            char_positions[eid] = {'x': view_data['x'], 'y': view_data['y'], 'icon_x': view_data['icon_x']}
            
            self.field_renderer.draw_home_marker(view_data['home_x'], view_data['home_y'])
            self.field_renderer.draw_character_icon(
                view_data['icon_x'], view_data['y'], 
                view_data['team_color'], view_data['part_status'], view_data['border_color']
            )
            self.field_renderer.draw_text(view_data['name'], (view_data['x'] - 20, view_data['y'] - 25), font_type='medium')
        return char_positions

    def _render_target_marker(self, context, flow, char_positions):
        """メニュー選択中に予定ターゲットを示すマーカーを表示"""
        target_eid = BattleViewModel.get_active_target_eid(self.world, context, flow)
        if target_eid and target_eid in char_positions:
            self.field_renderer.draw_target_marker(target_eid, char_positions)

    def _render_target_indication_line(self, context, flow, char_positions):
        """攻撃実行前のターゲットライン表示"""
        atk_id, tgt_id = CutinViewModel.get_event_actor_ids(self.world, flow)
        
        if atk_id in char_positions and tgt_id in char_positions:
            start_pos, end_pos = char_positions[atk_id], char_positions[tgt_id]
            self.field_renderer.draw_flow_line(
                (start_pos['icon_x'], start_pos['y'] + 20), 
                (end_pos['icon_x'], end_pos['y'] + 20), 
                flow.target_line_offset
            )

    def _render_ui(self, context, flow):
        show_input_guidance = flow.current_phase in [BattlePhase.LOG_WAIT, BattlePhase.ATTACK_DECLARATION, BattlePhase.CUTIN_RESULT]
        display_logs = [] if flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT] else context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:]
        
        self.ui_renderer.draw_message_window(display_logs, show_input_guidance)
        
        if flow.current_phase == BattlePhase.INPUT:
            eid = context.current_turn_entity_id
            if eid:
                actor_name = self.world.entities[eid]['medal'].nickname
                buttons = BattleViewModel.build_action_menu_data(self.world, eid)
                self.ui_renderer.draw_action_menu(actor_name, buttons, context.selected_menu_index)
        
        if flow.current_phase == BattlePhase.GAME_OVER:
            self.ui_renderer.draw_game_over(flow.winner)

    def _render_cutin(self, context, flow):
        # ViewModelが座標計算を全て終わらせた「State」を生成する
        state = CutinViewModel.build_action_state(self.world, flow)
        if not state: return
        # Rendererは渡されたStateをそのまま描画する
        self.cutin_renderer.draw(state)