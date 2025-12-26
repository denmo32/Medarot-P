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

        if context.game_over:
            return

        # 1. メッセージ送り待ち
        if context.waiting_for_input:
            if input_comp.mouse_clicked or input_comp.key_z:
                # 保留中のメッセージがある場合は次を表示
                if context.pending_logs:
                    context.battle_log.clear()
                    context.battle_log.append(context.pending_logs.pop(0))
                else:
                    # 保留なしなら終了
                    context.waiting_for_input = False
                    context.battle_log.clear()
                    context.execution_target_id = None # ターゲット表示終了
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

        # --- キーボードによるインデックス操作 ---
        if input_comp.key_left:
            context.selected_menu_index = (context.selected_menu_index - 1) % 4
        elif input_comp.key_right:
            context.selected_menu_index = (context.selected_menu_index + 1) % 4

        # --- マウスホバーによるインデックス同期 & クリック判定 ---
        mouse_selected = -1
        for i in range(4):
            bx = padding + i * (button_width + button_padding)
            if bx <= input_comp.mouse_x <= bx + button_width and button_y <= input_comp.mouse_y <= button_y + button_height:
                mouse_selected = i
                context.selected_menu_index = i # ホバーでインデックス更新

        # --- 決定処理 (Zキー or クリック) ---
        do_execute = input_comp.key_z or (input_comp.mouse_clicked and mouse_selected != -1)
        
        if not do_execute:
            return

        # 選択内容の決定
        selected_action = None
        selected_part = None

        def get_part_hp(part_type):
            part_id = part_list.parts.get(part_type)
            if part_id:
                p_comps = self.world.entities.get(part_id)
                h = p_comps.get('health') if p_comps else None
                return h.hp if h else 0
            return 0

        idx = context.selected_menu_index
        if idx == 0: # 頭部
            if get_part_hp('head') > 0:
                selected_action, selected_part = "attack", "head"
        elif idx == 1: # 右腕
            if get_part_hp('right_arm') > 0:
                selected_action, selected_part = "attack", "right_arm"
        elif idx == 2: # 左腕
            if get_part_hp('left_arm') > 0:
                selected_action, selected_part = "attack", "left_arm"
        elif idx == 3: # スキップ
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
            context.selected_menu_index = 0 # リセット

            if context.waiting_queue and context.waiting_queue[0] == eid:
                context.waiting_queue.pop(0)