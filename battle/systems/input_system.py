"""入力処理システム"""

from core.ecs import System
from battle.utils import calculate_action_times, calculate_action_menu_layout
from battle.constants import BattlePhase, ActionType, PartType, GaugeStatus

class InputSystem(System):
    """ユーザー入力を処理し、バトルフローに応じた操作を行う"""
    
    def update(self, dt: float):
        inputs = self.world.get_entities_with_components('input')
        if not inputs: return
        input_comp = inputs[0][1]['input']

        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return
        context = entities[0][1]['battlecontext']
        flow = entities[0][1]['battleflow']

        if flow.current_phase == BattlePhase.GAME_OVER:
            return

        if flow.current_phase == BattlePhase.LOG_WAIT:
            self._handle_log_wait(input_comp, context)
            return

        if flow.current_phase == BattlePhase.INPUT:
            self._handle_action_selection(context, flow, input_comp)

    def _handle_log_wait(self, input_comp, context):
        if input_comp.mouse_clicked or input_comp.key_z:
            if context.pending_logs:
                context.battle_log.clear()
                context.battle_log.append(context.pending_logs.pop(0))
            else:
                context.battle_log.clear()

    def _handle_action_selection(self, context, flow, input_comp):
        eid = context.current_turn_entity_id
        if eid is None or eid not in self.world.entities:
            flow.current_phase = BattlePhase.IDLE
            return

        # キー操作によるメニュー移動
        self._process_menu_navigation(input_comp, context)

        # 決定キーまたはクリック時の処理
        if input_comp.key_z or input_comp.mouse_clicked:
            self._confirm_action(eid, context, flow)

    def _process_menu_navigation(self, input_comp, context):
        # キーボード
        if input_comp.key_left:
            context.selected_menu_index = (context.selected_menu_index - 1) % 4
        elif input_comp.key_right:
            context.selected_menu_index = (context.selected_menu_index + 1) % 4

        # マウスホバー
        button_layout = calculate_action_menu_layout(4)
        for i, rect in enumerate(button_layout):
            if rect['x'] <= input_comp.mouse_x <= rect['x'] + rect['w'] and \
               rect['y'] <= input_comp.mouse_y <= rect['y'] + rect['h']:
                context.selected_menu_index = i

    def _confirm_action(self, eid, context, flow):
        comps = self.world.entities[eid]
        gauge = comps['gauge']
        part_list = comps['partlist']

        action, part = None, None
        idx = context.selected_menu_index
        parts_keys = [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]
        
        if idx < 3:
            p_type = parts_keys[idx]
            p_id = part_list.parts.get(p_type)
            if p_id and self.world.entities[p_id]['health'].hp > 0:
                action, part = ActionType.ATTACK, p_type
        else:
            action = ActionType.SKIP

        if action:
            self._apply_action(eid, action, part, gauge, part_list, context, flow)

    def _apply_action(self, eid, action, part, gauge, part_list, context, flow):
        gauge.selected_action, gauge.selected_part = action, part
        
        if part:
            p_id = part_list.parts.get(part)
            atk = self.world.entities[p_id]['attack'].attack
            gauge.charging_time, gauge.cooldown_time = calculate_action_times(atk)

        # チャージ開始
        gauge.status, gauge.progress = GaugeStatus.CHARGING, 0.0
        
        # フェーズ遷移
        context.current_turn_entity_id = None
        flow.current_phase = BattlePhase.IDLE
        
        if context.waiting_queue and context.waiting_queue[0] == eid:
            context.waiting_queue.pop(0)