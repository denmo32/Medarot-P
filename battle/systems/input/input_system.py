"""入力処理システム"""

from core.ecs import System
from components.action_command import ActionCommandComponent
from battle.constants import BattlePhase, ActionType, MENU_PART_ORDER
from battle.presentation.layout_utils import calculate_action_menu_layout
from battle.domain.utils import get_battle_state

class InputSystem(System):
    """ユーザー入力を処理し、バトルフローに応じた操作を行う"""
    
    def update(self, dt: float):
        inputs = self.world.get_entities_with_components('input')
        if not inputs: return
        input_comp = inputs[0][1]['input']

        context, flow = get_battle_state(self.world)
        if not context or not flow: return

        if flow.current_phase == BattlePhase.GAME_OVER: return

        if flow.current_phase == BattlePhase.LOG_WAIT:
            self._handle_log_wait(input_comp, context)
            return

        if flow.current_phase == BattlePhase.ATTACK_DECLARATION:
            self._handle_attack_declaration_wait(input_comp, context, flow)
            return

        if flow.current_phase == BattlePhase.CUTIN_RESULT:
            self._handle_cutin_result(input_comp, context, flow)
            return

        if flow.current_phase == BattlePhase.INPUT:
            self._handle_action_selection(context, flow, input_comp)

    def _handle_log_wait(self, input_comp, context):
        if input_comp.mouse_clicked or input_comp.btn_ok:
            if context.pending_logs:
                context.battle_log.clear()
                context.battle_log.append(context.pending_logs.pop(0))
            else:
                context.battle_log.clear()

    def _handle_attack_declaration_wait(self, input_comp, context, flow):
        if input_comp.mouse_clicked or input_comp.btn_ok:
            context.battle_log.clear()
            flow.current_phase = BattlePhase.CUTIN
            from battle.constants import BattleTiming
            flow.phase_timer = BattleTiming.CUTIN_ANIMATION

    def _handle_cutin_result(self, input_comp, context, flow):
        if not context.battle_log and context.pending_logs:
             context.battle_log.append(context.pending_logs.pop(0))

        if input_comp.mouse_clicked or input_comp.btn_ok:
            if context.pending_logs:
                context.battle_log.clear()
                context.battle_log.append(context.pending_logs.pop(0))
            else:
                context.battle_log.clear()
                flow.current_phase = BattlePhase.IDLE
                flow.active_actor_id = None
                if flow.processing_event_id is not None:
                    self.world.delete_entity(flow.processing_event_id)
                    flow.processing_event_id = None

    def _handle_action_selection(self, context, flow, input_comp):
        eid = context.current_turn_entity_id
        if eid is None or eid not in self.world.entities:
            flow.current_phase = BattlePhase.IDLE
            return

        menu_items_count = len(MENU_PART_ORDER) + 1
        self._process_menu_navigation(input_comp, context, menu_items_count)

        if input_comp.btn_ok or input_comp.mouse_clicked:
            if input_comp.mouse_clicked:
                idx = self._get_menu_index_at_mouse(input_comp.mouse_x, input_comp.mouse_y, menu_items_count)
                if idx is not None:
                    context.selected_menu_index = idx
                    self._issue_command(eid, context)
            else:
                self._issue_command(eid, context)

    def _process_menu_navigation(self, input_comp, context, item_count):
        if input_comp.btn_left:
            context.selected_menu_index = (context.selected_menu_index - 1) % item_count
        elif input_comp.btn_right:
            context.selected_menu_index = (context.selected_menu_index + 1) % item_count

        mouse_idx = self._get_menu_index_at_mouse(input_comp.mouse_x, input_comp.mouse_y, item_count)
        if mouse_idx is not None:
            context.selected_menu_index = mouse_idx

    def _get_menu_index_at_mouse(self, mx, my, button_count) -> int | None:
        layout = calculate_action_menu_layout(button_count)
        for i, rect in enumerate(layout):
            if rect.collidepoint(mx, my):
                return i
        return None

    def _issue_command(self, eid, context):
        part_list = self.world.entities[eid]['partlist']
        idx = context.selected_menu_index
        
        if idx < len(MENU_PART_ORDER):
            p_type = MENU_PART_ORDER[idx]
            p_id = part_list.parts.get(p_type)
            if p_id and self.world.entities[p_id]['health'].hp > 0:
                self.world.add_component(eid, ActionCommandComponent(ActionType.ATTACK, p_type))
        else:
            self.world.add_component(eid, ActionCommandComponent(ActionType.SKIP))