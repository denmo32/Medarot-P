"""描画ロジック（データ加工）を担当するシステム"""

from core.ecs import System
from config import GAME_PARAMS, COLORS
from battle.constants import BattlePhase, MENU_PART_ORDER, TeamType
from battle.view_model import BattleViewModel, CutinViewModel
from ui.cutin_renderer import CutinRenderer

class RenderSystem(System):
    """Worldのコンポーネントから描画用データを抽出しRendererへ渡す"""
    
    def __init__(self, world, field_renderer, ui_renderer):
        super().__init__(world)
        self.field_renderer = field_renderer
        self.ui_renderer = ui_renderer
        # CutinRendererの初期化
        self.cutin_renderer = CutinRenderer(field_renderer.screen)

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context, flow = entities[0][1]['battlecontext'], entities[0][1]['battleflow']

        self.field_renderer.clear()
        self.field_renderer.draw_field_guides()
        
        # 1. フィールド上のキャラクター描画
        char_positions = self._render_characters(context, flow)
        
        # 2. ターゲットマーカーと指示線の描画
        self._render_target_marker(context, flow, char_positions)
        self._render_target_indication_line(context, flow, char_positions)
        
        # 3. UIウィンドウとログの描画
        self._render_ui(context, flow)

        # 4. カットイン演出の描画（オーバーレイ）
        if flow.current_phase == BattlePhase.CUTIN or flow.current_phase == BattlePhase.CUTIN_RESULT:
            self._render_cutin(context, flow)

        self.field_renderer.present()

    def _render_characters(self, context, flow):
        char_positions = {}
        # 描画対象のエンティティを取得
        for eid, _ in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'medal'):
            # ViewModelを使用して描画データを取得
            view_data = BattleViewModel.get_character_view_data(self.world, eid, context, flow)
            
            char_positions[eid] = {
                'x': view_data['x'], 
                'y': view_data['y'], 
                'icon_x': view_data['icon_x']
            }
            
            # ホームマーカー
            self.field_renderer.draw_home_marker(view_data['home_x'], view_data['home_y'])
            
            # キャラクターアイコン
            self.field_renderer.draw_character_icon(
                view_data['icon_x'], 
                view_data['y'], 
                view_data['team_color'], 
                view_data['part_status'], 
                view_data['border_color']
            )
            
            # 名前
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
        """TARGET_INDICATIONフェーズ等のアニメーションライン描画"""
        target_line_phases = [
            BattlePhase.TARGET_INDICATION,
            BattlePhase.ATTACK_DECLARATION,
            BattlePhase.CUTIN,
            BattlePhase.CUTIN_RESULT
        ]
        if flow.current_phase not in target_line_phases:
            return
            
        event_eid = flow.processing_event_id
        if event_eid is None: return
        
        event_comps = self.world.try_get_entity(event_eid)
        if not event_comps or 'actionevent' not in event_comps: return
        
        event = event_comps['actionevent']
        attacker_id = event.attacker_id
        target_id = event.current_target_id
        
        if attacker_id in char_positions and target_id in char_positions:
            start_pos = char_positions[attacker_id]
            end_pos = char_positions[target_id]
            
            sp = (start_pos['icon_x'], start_pos['y'] + 20)
            ep = (end_pos['icon_x'], end_pos['y'] + 20)
            
            self.field_renderer.draw_flow_line(sp, ep, flow.target_line_offset)

    def _render_ui(self, context, flow):
        # ログとガイドの表示
        show_input_guidance = (flow.current_phase == BattlePhase.LOG_WAIT or 
                               flow.current_phase == BattlePhase.ATTACK_DECLARATION or
                               flow.current_phase == BattlePhase.CUTIN_RESULT)
        
        # カットイン中はウィンドウ内のログを隠す
        if flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT]:
            display_logs = []
        else:
            display_logs = context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:]

        self.ui_renderer.draw_message_window(display_logs, show_input_guidance)
        
        # コマンドメニュー
        if flow.current_phase == BattlePhase.INPUT:
            eid = context.current_turn_entity_id
            if eid:
                comps = self.world.entities[eid]
                buttons = [{'label': self.world.entities[p_id]['name'].name, 'enabled': self.world.entities[p_id]['health'].hp > 0} 
                           for p_id in [comps['partlist'].parts.get(k) for k in MENU_PART_ORDER] if p_id]
                buttons.append({'label': "スキップ", 'enabled': True})
                self.ui_renderer.draw_action_menu(comps['medal'].nickname, buttons, context.selected_menu_index)
        
        # ゲームオーバー
        if flow.current_phase == BattlePhase.GAME_OVER:
            self.ui_renderer.draw_game_over(flow.winner)

    def _render_cutin(self, context, flow):
        """
        カットイン演出に必要なデータを収集してRendererへ渡す。
        """
        event_eid = flow.processing_event_id
        if event_eid is None: return
        
        event_comps = self.world.try_get_entity(event_eid)
        if not event_comps or 'actionevent' not in event_comps: return
        
        event = event_comps['actionevent']
        attacker_comps = self.world.try_get_entity(event.attacker_id)
        target_comps = self.world.try_get_entity(event.current_target_id)
        
        if not attacker_comps or not target_comps: return

        # 攻撃特性の取得
        attack_trait = None
        if event.part_type:
             p_id = attacker_comps['partlist'].parts.get(event.part_type)
             if p_id:
                 p_comps = self.world.try_get_entity(p_id)
                 if p_comps and 'attack' in p_comps:
                     attack_trait = p_comps['attack'].trait

        # 進行度取得
        progress = flow.cutin_progress if flow.current_phase == BattlePhase.CUTIN else 1.0
        
        # データ構築（ViewModel使用）
        attacker_data = CutinViewModel.create_character_data(self.world, event.attacker_id)
        target_data = CutinViewModel.create_character_data(self.world, event.current_target_id)
        
        # HPデータの生成もBattleViewModelのロジックを再利用
        attacker_hp_data = BattleViewModel.build_hp_data(self.world, attacker_comps['partlist'])
        target_hp_data = BattleViewModel.build_hp_data(self.world, target_comps['partlist'])
        
        # 描画用データの整形（CutinRendererの負担を減らす）
        attacker_visual = CutinViewModel.create_character_visual_state(attacker_data, attacker_hp_data, show_hp=False)
        target_visual = CutinViewModel.create_character_visual_state(target_data, target_hp_data, show_hp=True)
        
        hit_result = event.calculation_result
        is_enemy_attack = (attacker_comps['team'].team_type == TeamType.ENEMY)

        # 描画委譲
        self.cutin_renderer.draw(
            attacker_visual, target_visual,
            progress, hit_result, 
            mirror=is_enemy_attack,
            attack_trait=attack_trait
        )