"""描画ロジック（データ加工）を担当するシステム"""

from core.ecs import System
from config import COLORS, GAME_PARAMS

try:
    from data.parts_data_manager import get_parts_manager
    PARTS_MANAGER_AVAILABLE = True
except ImportError:
    PARTS_MANAGER_AVAILABLE = False

class RenderSystem(System):
    """ECS Worldからデータを取得・計算し、Rendererに渡すシステム"""
    
    def __init__(self, world, renderer):
        super().__init__(world)
        self.renderer = renderer
        self.parts_manager = get_parts_manager() if PARTS_MANAGER_AVAILABLE else None

    def update(self, dt: float = 0.016):
        contexts = self.world.get_entities_with_components('battlecontext')
        if not contexts: return
        context = contexts[0][1]['battlecontext']

        self.renderer.clear()
        self.renderer.draw_team_titles("プレイヤーチーム", "エネミーチーム")

        # キャラクター描画データの準備
        for eid, comps in self.world.entities.items():
            if all(k in comps for k in ('render', 'position', 'gauge', 'partlist', 'team', 'defeated')):
                self._process_entity_render(eid, comps)

        # メッセージウィンドウデータの準備
        logs = context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:]
        self.renderer.draw_message_window(logs, context.waiting_for_input)

        # アクションメニューデータの準備
        if context.waiting_for_action and not context.game_over:
            self._process_action_menu(context)

        # ゲームオーバーデータの準備
        if context.game_over:
            self.renderer.draw_game_over(context.winner)

        self.renderer.present()

    def _process_entity_render(self, eid, comps):
        if comps['defeated'].is_defeated: return

        pos, gauge, team, name = comps['position'], comps['gauge'], comps['team'], comps['name']
        
        # アイコン座標計算
        icon_x = self._calculate_icon_x(pos.x, gauge.status, gauge.progress, team.team_type)
        self.renderer.draw_character_info(pos.x, pos.y, name.name, icon_x, team.team_color)

        # HPバーデータ計算
        hp_data = []
        parts_order = ['head', 'right_arm', 'left_arm', 'leg']
        colors = [COLORS['HP_HEAD'], COLORS['HP_RIGHT_ARM'], COLORS['HP_LEFT_ARM'], COLORS['HP_LEG']]
        
        for p_key, p_color in zip(parts_order, colors):
            p_id = comps['partlist'].parts.get(p_key)
            if p_id:
                h = self.world.entities[p_id].get('health')
                ratio = h.hp / h.max_hp if h and h.max_hp > 0 else 0
                hp_data.append({'ratio': ratio, 'color': p_color})
        
        self.renderer.draw_hp_bars(pos.x, pos.y, hp_data)

    def _calculate_icon_x(self, x, status, progress, team_type):
        center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
        exec_offset = 40
        if team_type == "player":
            if status == "charging": return x + (progress / 100.0) * (center_x - exec_offset - x)
            if status == "executing": return center_x - exec_offset
            if status == "cooldown": return (center_x - exec_offset) - (progress / 100.0) * ((center_x - exec_offset) - x)
            return x
        else:
            end_x = x + GAME_PARAMS['GAUGE_WIDTH']
            if status == "charging": return end_x - (progress / 100.0) * (end_x - (center_x + exec_offset))
            if status == "executing": return center_x + exec_offset
            if status == "cooldown": return (center_x + exec_offset) + (progress / 100.0) * (end_x - (center_x + exec_offset))
            return end_x

    def _process_action_menu(self, context):
        eid = context.current_turn_entity_id
        if eid not in self.world.entities: return
        comps = self.world.entities[eid]
        
        buttons = []
        parts_keys = ['head', 'right_arm', 'left_arm']
        is_player = comps['team'].team_type == "player"
        labels = self.parts_manager.get_button_labels(is_player) if self.parts_manager else {}

        for key in parts_keys:
            p_id = comps['partlist'].parts.get(key)
            hp = self.world.entities[p_id].get('health').hp if p_id else 0
            buttons.append({
                'label': labels.get(key, key),
                'enabled': hp > 0
            })
        
        buttons.append({'label': "スキップ", 'enabled': True})
        self.renderer.draw_action_menu(comps['name'].name, buttons)