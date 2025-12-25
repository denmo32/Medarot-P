"""入力処理システム"""

from core.ecs import System
from config import GAME_PARAMS
from components.battle import GaugeComponent
from battle.utils import calculate_action_times

class InputSystem(System):
    """ユーザー入力を処理し、UI状態遷移や行動選択を行うシステム"""
    
    def update(self, dt: float = 0.016):
        inputs = self.world.get_entities_with_components('input')
        if not inputs: return
        input_comp = inputs[0][1]['input']

        contexts = self.world.get_entities_with_components('battlecontext')
        if not contexts: return
        context = contexts[0][1]['battlecontext']

        if not input_comp.mouse_clicked:
            return

        mouse_x = input_comp.mouse_x
        mouse_y = input_comp.mouse_y

        if context.game_over:
            return

        # 2. メッセージ送り待ち
        if context.waiting_for_input:
            context.waiting_for_input = False
            context.battle_log.clear()
            return

        # 3. 行動選択待ち
        if context.waiting_for_action:
            self._handle_action_selection(context, mouse_x, mouse_y)

    def _handle_action_selection(self, context, mouse_x, mouse_y):
        eid = context.current_turn_entity_id
        if eid is None or eid not in self.world.entities:
            context.waiting_for_action = False
            return

        comps = self.world.entities[eid]
        gauge_comp = comps.get('gauge')
        part_list = comps.get('partlist')

        # レイアウト定数
        ui_cfg = GAME_PARAMS['UI']
        window_y = GAME_PARAMS['MESSAGE_WINDOW_Y']
        padding = GAME_PARAMS['MESSAGE_WINDOW_PADDING']
        button_y = window_y + GAME_PARAMS['MESSAGE_WINDOW_HEIGHT'] - ui_cfg['BTN_Y_OFFSET']
        button_width = ui_cfg['BTN_WIDTH']
        button_height = ui_cfg['BTN_HEIGHT']
        button_padding = ui_cfg['BTN_PADDING']

        selected_action = None
        selected_part = None

        def is_clicked(idx):
            bx = padding + idx * (button_width + button_padding)
            return bx <= mouse_x <= bx + button_width and button_y <= mouse_y <= button_y + button_height

        def get_part_hp(part_type):
            part_id = part_list.parts.get(part_type)
            if part_id:
                p_comps = self.world.entities.get(part_id)
                h = p_comps.get('health') if p_comps else None
                return h.hp if h else 0
            return 0

        # 各ボタン判定
        if is_clicked(0): # 頭部
            if get_part_hp('head') > 0:
                selected_action, selected_part = "attack", "head"
        elif is_clicked(1): # 右腕
            if get_part_hp('right_arm') > 0:
                selected_action, selected_part = "attack", "right_arm"
        elif is_clicked(2): # 左腕
            if get_part_hp('left_arm') > 0:
                selected_action, selected_part = "attack", "left_arm"
        elif is_clicked(3): # スキップ
            selected_action = "skip"

        if selected_action:
            gauge_comp.selected_action = selected_action
            gauge_comp.selected_part = selected_part
            
            if selected_part:
                part_id = part_list.parts.get(selected_part)
                attack_comp = self.world.entities[part_id].get('attack')
                if attack_comp:
                    c_t, cd_t = calculate_action_times(attack_comp.attack)
                    gauge_comp.charging_time, gauge_comp.cooldown_time = c_t, cd_t
            
            gauge_comp.status = GaugeComponent.CHARGING
            gauge_comp.progress = 0.0
            context.current_turn_entity_id = None
            context.waiting_for_action = False
            
            if context.waiting_queue and context.waiting_queue[0] == eid:
                context.waiting_queue.pop(0)