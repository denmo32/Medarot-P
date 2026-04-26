"""入力処理システム"""

from battle.systems.battle_system_base import BattleSystemBase
from components.action_command_component import ActionCommandComponent
from ui.config import MENU_PART_ORDER
from battle.constants import BattlePhase, ActionType, BattleTiming
from battle.mechanics.flow import FlowMechanics, PhaseTransition

class InputSystem(BattleSystemBase):
    """
    ユーザー入力を現在のフェーズに応じた処理に振り分ける。
    
    リファクタリング後：
    - 座標判定は Scene 側で行われ、InputComponent.action_commands にキューイングされる
    - この System は「コマンドを消費して ActionCommandComponent を生成する」のみを担当
    - 画面座標の概念は一切持たない（ECS と UI の完全分離）
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
        # 入力コンポーネント取得
        _, input_comps = self.world.get_first_entity('input')
        if not input_comps:
            return
        input_comp = input_comps['input']

        context = self.context
        flow = self.flow
        if not context or not flow:
            return

        handler = self.handlers.get(flow.current_phase)
        if handler:
            handler(input_comp, context, flow)

    def _handle_log_wait(self, input_comp, context, flow):
        if input_comp.btn_ok:
            if context.pending_logs:
                context.battle_log.clear()
                context.battle_log.append(context.pending_logs.pop(0))
            else:
                context.battle_log.clear()

    def _handle_attack_declaration_wait(self, input_comp, context, flow):
        if input_comp.btn_ok:
            context.battle_log.clear()
            FlowMechanics.apply_transition(self.world, PhaseTransition(
                next_phase=BattlePhase.CUTIN,
                timer=BattleTiming.CUTIN_ANIMATION
            ))

    def _handle_cutin_result(self, input_comp, context, flow):
        if not context.battle_log and context.pending_logs:
             context.battle_log.append(context.pending_logs.pop(0))

        if input_comp.btn_ok:
            if context.pending_logs:
                context.battle_log.clear()
                context.battle_log.append(context.pending_logs.pop(0))
            else:
                context.battle_log.clear()
                self._clear_execution_state(flow)

    def _clear_execution_state(self, flow):
        event_id = flow.processing_event_id
        if event_id is not None:
            flow.processing_event_id = None
            self.world.delete_entity(event_id)

        FlowMechanics.apply_transition(self.world, PhaseTransition(next_phase=BattlePhase.IDLE))

    def _handle_action_selection(self, input_comp, context, flow):
        """
        INPUT フェーズでの入力処理。
        
        リファクタリング後：
        - キーボード/マウスによる選択変更は input_comp.selected_menu_index に設定される
        - 決定入力は input_comp.action_commands にキューイングされている
        - このメソッドは action_commands を消費して ActionCommandComponent を生成するだけ
        """
        eid = context.current_turn_entity_id
        if eid is None or eid not in self.world.entities:
            FlowMechanics.apply_transition(self.world, PhaseTransition(next_phase=BattlePhase.IDLE))
            return

        # 選択インデックスの更新（Scene から渡されたコマンドを反映）
        if input_comp.selected_menu_index is not None:
            context.selected_menu_index = input_comp.selected_menu_index

        # action_commands キューを処理
        if input_comp.action_commands:
            for action_type, part_type in input_comp.action_commands:
                self._execute_command(eid, action_type, part_type)
            input_comp.action_commands.clear()

    def _execute_command(self, eid: int, action_type: str, part_type: str | None):
        """
        キューイングされたコマンドを実行する。
        
        引数：
            eid: 行動主体エンティティ ID
            action_type: "attack", "skip" など
            part_type: 対象パーツ（"head", "right_arm" など、skip の場合は None）
        """
        if action_type == ActionType.ATTACK and part_type:
            # 攻撃コマンド：対象パーツが有効か確認
            comps = self.world.try_get_entity(eid)
            if not comps or 'partlist' not in comps:
                return

            part_list = comps['partlist']
            p_id = part_list.parts.get(part_type)
            p_comps = self.world.try_get_entity(p_id)

            if p_comps and 'health' in p_comps and p_comps['health'].hp > 0:
                self.world.add_component(eid, ActionCommandComponent(ActionType.ATTACK, part_type))
                return

        # スキップコマンド、または無効な攻撃コマンド
        self.world.add_component(eid, ActionCommandComponent(ActionType.SKIP))
