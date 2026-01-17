"""描画ロジック（データ加工）を担当するシステム"""

import pygame
from core.ecs import System
from config import GAME_PARAMS
from battle.utils import calculate_current_x
from battle.constants import PartType, GaugeStatus, BattlePhase, TeamType, PART_LABELS, MENU_PART_ORDER
from ui.cutin_renderer import CutinRenderer

class RenderSystem(System):
    """Worldのコンポーネントから描画用データを抽出しRendererへ渡す"""
    
    def __init__(self, world, renderer):
        super().__init__(world)
        self.renderer = renderer
        self.cutin_renderer = CutinRenderer(renderer.screen, renderer)
        self.hp_bar_order = [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context, flow = entities[0][1]['battlecontext'], entities[0][1]['battleflow']

        self.renderer.clear()
        self.renderer.draw_field_guides()
        char_positions = self._render_characters(context, flow)
        
        self._render_target_marker(context, flow, char_positions)
        self._render_target_indication_line(context, flow, char_positions)
        
        self._render_ui(context, flow)

        # カットインはUIの上にさらに重ねる
        if flow.current_phase == BattlePhase.CUTIN or flow.current_phase == BattlePhase.CUTIN_RESULT:
            self._render_cutin(context, flow)

        self.renderer.present()

    def _render_characters(self, context, flow):
        char_positions = {}
        for eid, comps in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'medal'):
            pos, gauge, team, medal = comps['position'], comps['gauge'], comps['team'], comps['medal']
            
            icon_x = calculate_current_x(pos.x, gauge.status, gauge.progress, team.team_type)
            char_positions[eid] = {'x': pos.x, 'y': pos.y, 'icon_x': icon_x}
            
            # ホーム位置と本体
            self.renderer.draw_home_marker(pos.x + (GAME_PARAMS['GAUGE_WIDTH'] if team.team_type == TeamType.ENEMY else 0), pos.y)
            border = self._get_border_color(eid, gauge, context, flow)
            self.renderer.draw_character_icon(icon_x, pos.y, team.team_color, border)
            self.renderer.draw_text(medal.nickname, (pos.x - 20, pos.y - 25), font_type='medium')

            # HP
            hp_data = self._build_hp_data(comps['partlist'])
            self.renderer.draw_hp_bars(pos.x, pos.y, hp_data)
        return char_positions

    def _get_border_color(self, eid, gauge, context, flow):
        from config import COLORS
        if eid == flow.active_actor_id or eid in context.waiting_queue or gauge.status == GaugeStatus.ACTION_CHOICE:
            return COLORS.get('BORDER_WAIT')
        if gauge.status == GaugeStatus.CHARGING:
            return COLORS.get('BORDER_CHARGE')
        if gauge.status == GaugeStatus.COOLDOWN:
            return COLORS.get('BORDER_COOLDOWN')
        return None

    def _build_hp_data(self, part_list_comp):
        hp_data = []
        for p_key in self.hp_bar_order:
            p_id = part_list_comp.parts.get(p_key)
            if p_id is not None:
                h = self.world.entities[p_id]['health']
                hp_data.append({
                    'label': PART_LABELS.get(p_key, ""),
                    'current': int(h.display_hp),
                    'max': h.max_hp,
                    'ratio': h.display_hp / h.max_hp if h.max_hp > 0 else 0
                })
        return hp_data

    def _render_target_marker(self, context, flow, char_positions):
        target_eid = None
        if flow.current_phase == BattlePhase.INPUT:
            eid = context.current_turn_entity_id
            if eid and context.selected_menu_index < len(MENU_PART_ORDER):
                target_data = self.world.entities[eid]['gauge'].part_targets.get(MENU_PART_ORDER[context.selected_menu_index])
                if target_data: target_eid = target_data[0]
        elif flow.processing_event_id is not None and flow.current_phase != BattlePhase.TARGET_INDICATION:
             pass
        
        if target_eid:
            self.renderer.draw_target_marker(target_eid, char_positions)

    def _render_target_indication_line(self, context, flow, char_positions):
        """TARGET_INDICATIONフェーズでのアニメーション描画"""
        if flow.current_phase != BattlePhase.TARGET_INDICATION:
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
            
            # アイコンの中心座標（icon_x, y+20 が中心）
            sp = (start_pos['icon_x'], start_pos['y'] + 20)
            ep = (end_pos['icon_x'], end_pos['y'] + 20)
            
            # 継続時間を使ったアニメーション
            current_time = pygame.time.get_ticks() / 1000.0
            
            self.renderer.draw_flow_line(sp, ep, current_time)

    def _render_ui(self, context, flow):
        # メッセージウィンドウの表示条件に CUTIN_RESULT も追加
        show_message = (flow.current_phase == BattlePhase.LOG_WAIT or 
                        flow.current_phase == BattlePhase.ATTACK_DECLARATION or
                        flow.current_phase == BattlePhase.CUTIN_RESULT)
        
        self.renderer.draw_message_window(context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:], show_message)
        
        if flow.current_phase == BattlePhase.INPUT:
            eid = context.current_turn_entity_id
            if eid:
                comps = self.world.entities[eid]
                buttons = [{'label': self.world.entities[p_id]['name'].name, 'enabled': self.world.entities[p_id]['health'].hp > 0} 
                           for p_id in [comps['partlist'].parts.get(k) for k in MENU_PART_ORDER] if p_id]
                buttons.append({'label': "スキップ", 'enabled': True})
                self.renderer.draw_action_menu(comps['medal'].nickname, buttons, context.selected_menu_index)
        
        if flow.current_phase == BattlePhase.GAME_OVER:
            self.renderer.draw_game_over(flow.winner)

    def _render_cutin(self, context, flow):
        event_eid = flow.processing_event_id
        if event_eid is None: return
        
        event_comps = self.world.try_get_entity(event_eid)
        if not event_comps or 'actionevent' not in event_comps: return
        
        event = event_comps['actionevent']
        attacker_comps = self.world.try_get_entity(event.attacker_id)
        target_comps = self.world.try_get_entity(event.current_target_id)
        
        if not attacker_comps or not target_comps: return

        # 進行度取得（CUTINフェーズ以外は1.0=終了）
        progress = flow.cutin_progress if flow.current_phase == BattlePhase.CUTIN else 1.0
        
        attacker_data = {
            'name': attacker_comps['medal'].nickname,
            'color': attacker_comps['team'].team_color
        }
        target_data = {
            'name': target_comps['medal'].nickname,
            'color': target_comps['team'].team_color
        }
        
        # ヒット判定（計算結果がない場合はミス扱い）
        is_hit = False
        if event.calculation_result and event.calculation_result.get('is_hit'):
            is_hit = True

        # 攻撃側がエネミーなら左右反転（右→左の攻撃）
        is_enemy_attack = (attacker_comps['team'].team_type == TeamType.ENEMY)

        self.cutin_renderer.draw(attacker_data, target_data, progress, is_hit, mirror=is_enemy_attack)