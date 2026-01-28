"""入力処理システム"""

from core.ecs import System
from components.action_command_component import ActionCommandComponent
from battle.constants import BattlePhase, ActionType, MENU_PART_ORDER
from ui.battle.layout_utils import calculate_action_menu_layout
from battle.mechanics.flow import get_battle_state
from battle.mechanics.log import LogBuilder

class InputSystem(System):
    def update(self, dt: float):
        inputs = self.world.get_entities_with_components('input')
        if not inputs: return
        input_comp = inputs[0][1]['input']

        context, flow = get_battle_state(self.world)
        if not context or not flow: return

        if flow.current_phase == BattlePhase.GAME_OVER:
            return

        elif flow.current_phase == BattlePhase.LOG_WAIT:
            self._handle_log_wait(input_comp, context)

        elif flow.current_phase == BattlePhase.ATTACK_DECLARATION:
            self._handle_attack_declaration_wait(input_comp, context, flow)

        elif flow.current_phase == BattlePhase.CUTIN_RESULT:
            self._handle_cutin_result(input_comp, context, flow)

        elif flow.current_phase == BattlePhase.INPUT:
            self._handle_action_selection(input_comp, context, flow)

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

    def _handle_action_selection(self, input_comp, context, flow):
        eid = context.current_turn_entity_id
        if eid is None or eid not in self.world.entities:
            flow.current_phase = BattlePhase.IDLE
            return

        menu_items_count = len(MENU_PART_ORDER) + 1
        
        if input_comp.btn_left:
            context.selected_menu_index = (context.selected_menu_index - 1) % menu_items_count
        elif input_comp.btn_right:
            context.selected_menu_index = (context.selected_menu_index + 1) % menu_items_count

        mouse_idx = self._get_menu_index_at_mouse(input_comp.mouse_x, input_comp.mouse_y, menu_items_count)
        if mouse_idx is not None:
            context.selected_menu_index = mouse_idx

        if input_comp.btn_ok or input_comp.mouse_clicked:
            self._issue_command(eid, context)

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