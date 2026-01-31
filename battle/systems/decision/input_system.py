"""入力処理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from components.action_command_component import ActionCommandComponent
from battle.constants import BattlePhase, ActionType, MENU_PART_ORDER, BattleTiming
from battle.mechanics.log import LogBuilder

class InputSystem(BattleSystemBase):
    """
    ユーザー入力を現在のフェーズに応じた処理に振り分ける。
    座標による要素判定（Hit Test）はViewModelに委譲する。
    """
    def __init__(self, world, view_model):
        super().__init__(world)
        self.view_model = view_model
        self.handlers = {
            BattlePhase.LOG_WAIT: self._handle_log_wait,
            BattlePhase.ATTACK_DECLARATION: self._handle_attack_declaration_wait,
            BattlePhase.CUTIN_RESULT: self._handle_cutin_result,
            BattlePhase.INPUT: self._handle_action_selection
        }

    def update(self, dt: float):
        # 入力コンポーネント取得
        _, input_comps = self.world.get_first_entity('input')
        if not input_comps: return
        input_comp = input_comps['input']

        context, flow = self.battle_state
        if not context or not flow: return

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
        
        # キーボードによる選択変更
        if input_comp.btn_left:
            context.selected_menu_index = (context.selected_menu_index - 1) % menu_items_count
        elif input_comp.btn_right:
            context.selected_menu_index = (context.selected_menu_index + 1) % menu_items_count

        # マウス座標による選択変更（ViewModelに座標解釈を委譲）
        mouse_idx = self.view_model.hit_test_action_menu(input_comp.mouse_x, input_comp.mouse_y)
        if mouse_idx is not None:
            context.selected_menu_index = mouse_idx

        if input_comp.btn_ok or input_comp.mouse_clicked:
            self._issue_command(eid, context)

    def _issue_command(self, eid, context):
        comps = self.world.try_get_entity(eid)
        if not comps or 'partlist' not in comps: return
        part_list = comps['partlist']
        
        idx = context.selected_menu_index
        if idx < len(MENU_PART_ORDER):
            p_type = MENU_PART_ORDER[idx]
            p_id = part_list.parts.get(p_type)
            p_comps = self.world.try_get_entity(p_id)
            if p_comps and p_comps['health'].hp > 0:
                self.world.add_component(eid, ActionCommandComponent(ActionType.ATTACK, p_type))
        else:
            self.world.add_component(eid, ActionCommandComponent(ActionType.SKIP))