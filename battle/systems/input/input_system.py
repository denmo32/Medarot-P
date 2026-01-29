"""入力処理システム"""

from core.ecs import System
from components.action_command_component import ActionCommandComponent
from battle.constants import BattlePhase, ActionType, MENU_PART_ORDER, BattleTiming
from ui.battle.layout_utils import calculate_action_menu_layout
from battle.mechanics.flow import get_battle_state
from battle.mechanics.log import LogBuilder

class InputSystem(System):
    """
    ユーザー入力を現在のフェーズに応じた処理に振り分ける。
    フェーズごとのハンドラを定義し、ディスパッチすることで可読性を向上。
    """
    def __init__(self, world):
        super().__init__(world)
        self.handlers = {
            BattlePhase.LOG_WAIT: self._handle_log_wait,
            BattlePhase.ATTACK_DECLARATION: self._handle_attack_declaration_wait,
            BattlePhase.CUTIN_RESULT: self._handle_cutin_result,
            BattlePhase.INPUT: self._handle_action_selection
        }

    def update(self, dt: float):
        inputs = self.world.get_entities_with_components('input')
        if not inputs: return
        input_comp = inputs[0][1]['input']

        context, flow = get_battle_state(self.world)
        if not context or not flow: return

        # 現在のフェーズに対応するハンドラがあれば実行
        handler = self.handlers.get(flow.current_phase)
        if handler:
            handler(input_comp, context, flow)

    def _handle_log_wait(self, input_comp, context, flow):
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
                self._clear_execution_state(flow)

    def _clear_execution_state(self, flow):
        """実行状態のクリーンアップ"""
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
        
        # 方向入力によるインデックス更新
        if input_comp.btn_left:
            context.selected_menu_index = (context.selected_menu_index - 1) % menu_items_count
        elif input_comp.btn_right:
            context.selected_menu_index = (context.selected_menu_index + 1) % menu_items_count

        # マウスホバーによるインデックス更新
        mouse_idx = self._get_menu_index_at_mouse(input_comp.mouse_x, input_comp.mouse_y, menu_items_count)
        if mouse_idx is not None:
            context.selected_menu_index = mouse_idx

        # 決定処理
        if input_comp.btn_ok or input_comp.mouse_clicked:
            self._issue_command(eid, context)

    def _get_menu_index_at_mouse(self, mx, my, button_count) -> int | None:
        layout = calculate_action_menu_layout(button_count)
        for i, rect in enumerate(layout):
            if rect.collidepoint(mx, my):
                return i
        return None

    def _issue_command(self, eid, context):
        part_list = self.world.entities[eid].get('partlist')
        if not part_list: return
        
        idx = context.selected_menu_index
        if idx < len(MENU_PART_ORDER):
            p_type = MENU_PART_ORDER[idx]
            p_id = part_list.parts.get(p_type)
            if p_id and self.world.entities[p_id]['health'].hp > 0:
                self.world.add_component(eid, ActionCommandComponent(ActionType.ATTACK, p_type))
        else:
            self.world.add_component(eid, ActionCommandComponent(ActionType.SKIP))