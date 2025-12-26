"""入力処理システム"""

from core.ecs import System
from config import GAME_PARAMS
from battle.utils import calculate_action_times

class InputSystem(System):
    """ユーザー入力を処理し、バトルコンテキストやゲージ状態を更新する"""
    
    def update(self, dt: float):
        inputs = self.world.get_entities_with_components('input')
        if not inputs: return
        input_comp = inputs[0][1]['input']

        contexts = self.world.get_entities_with_components('battlecontext')
        if not contexts: return
        context = contexts[0][1]['battlecontext']

        if context.game_over: return

        # 1. メッセージ送り待ち
        if context.waiting_for_input:
            if input_comp.mouse_clicked or input_comp.key_z:
                if context.pending_logs:
                    context.battle_log.clear()
                    context.battle_log.append(context.pending_logs.pop(0))
                else:
                    context.waiting_for_input = False
                    context.battle_log.clear()
                    context.execution_target_id = None
            return

        # 2. 行動選択待ち
        if context.waiting_for_action:
            self._handle_action_selection(context, input_comp)

    def _handle_action_selection(self, context, input_comp):
        eid = context.current_turn_entity_id
        if eid is None or eid not in self.world.entities:
            context.waiting_for_action = False
            return

        comps = self.world.entities[eid]
        gauge = comps['gauge']
        part_list = comps['partlist']

        # キー操作
        if input_comp.key_left:
            context.selected_menu_index = (context.selected_menu_index - 1) % 4
        elif input_comp.key_right:
            context.selected_menu_index = (context.selected_menu_index + 1) % 4

        # マウスホバー同期（簡易。本来はRenderSystemのレイアウト情報を参照すべきだが、設定値から計算）
        ui_cfg = GAME_PARAMS['UI']
        button_y = GAME_PARAMS['MESSAGE_WINDOW_Y'] + GAME_PARAMS['MESSAGE_WINDOW_HEIGHT'] - ui_cfg['BTN_Y_OFFSET']
        for i in range(4):
            bx = GAME_PARAMS['MESSAGE_WINDOW_PADDING'] + i * (ui_cfg['BTN_WIDTH'] + ui_cfg['BTN_PADDING'])
            if bx <= input_comp.mouse_x <= bx + ui_cfg['BTN_WIDTH'] and button_y <= input_comp.mouse_y <= button_y + ui_cfg['BTN_HEIGHT']:
                context.selected_menu_index = i

        if not (input_comp.key_z or input_comp.mouse_clicked): return

        # 決定処理
        action, part = None, None
        idx = context.selected_menu_index
        parts_keys = ["head", "right_arm", "left_arm"]
        
        if idx < 3:
            p_type = parts_keys[idx]
            p_id = part_list.parts.get(p_type)
            if p_id and self.world.entities[p_id]['health'].hp > 0:
                action, part = "attack", p_type
        else:
            action = "skip"

        if action:
            gauge.selected_action, gauge.selected_part = action, part
            if part:
                p_id = part_list.parts.get(part)
                atk = self.world.entities[p_id]['attack'].attack
                gauge.charging_time, gauge.cooldown_time = calculate_action_times(atk)

            gauge.status, gauge.progress = gauge.CHARGING, 0.0
            context.current_turn_entity_id, context.waiting_for_action = None, False
            if context.waiting_queue and context.waiting_queue[0] == eid:
                context.waiting_queue.pop(0)