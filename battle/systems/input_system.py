"""入力処理システム"""

from core.ecs import System
from battle.utils import apply_action_command
from battle.constants import BattlePhase, ActionType, MENU_PART_ORDER, BattleTiming

class InputSystem(System):
    """ユーザー入力を処理し、バトルフローに応じた操作を行う"""
    
    def __init__(self, world, ui_renderer):
        super().__init__(world)
        self.ui_renderer = ui_renderer

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
            self._confirm_action(eid, context)

    def _process_menu_navigation(self, input_comp, context, item_count):
        # 1. キーボードによる選択
        if input_comp.btn_left:
            context.selected_menu_index = (context.selected_menu_index - 1) % item_count
        elif input_comp.btn_right:
            context.selected_menu_index = (context.selected_menu_index + 1) % item_count

        # 2. マウス座標による選択（レンダラーに空間判定を委譲）
        mouse_idx = self.ui_renderer.get_index_at_mouse((input_comp.mouse_x, input_comp.mouse_y), item_count)
        if mouse_idx is not None:
            context.selected_menu_index = mouse_idx

    def _confirm_action(self, eid, context):
        part_list = self.world.entities[eid]['partlist']
        action, part = None, None
        idx = context.selected_menu_index
        
        if idx < len(MENU_PART_ORDER):
            p_type = MENU_PART_ORDER[idx]
            p_id = part_list.parts.get(p_type)
            if p_id and self.world.entities[p_id]['health'].hp > 0:
                action, part = ActionType.ATTACK, p_type
        else:
            action = ActionType.SKIP

        if action:
            apply_action_command(self.world, eid, action, part)