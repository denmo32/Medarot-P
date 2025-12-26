"""入力処理システム"""

from core.ecs import System
from config import GAME_PARAMS
from battle.utils import calculate_action_times
from components.battle_flow import BattleFlowComponent

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

        if flow.current_phase == BattleFlowComponent.PHASE_GAME_OVER:
            return

        # 1. ログ送り待ち
        if flow.current_phase == BattleFlowComponent.PHASE_LOG_WAIT:
            if input_comp.mouse_clicked or input_comp.key_z:
                # pending_logs機能はDamageSystemで使用（ダメージ詳細など）
                # 現在のログ（battle_log）をクリアして次へ進む
                # 簡略化のため、battle_logを全消去してIDLEに戻るトリガーとする
                # (BattleFlowSystemが空になったことを検知してIDLEに戻す)
                
                # DamageSystem等がpending_logsに追加している場合、それをbattle_logに移す
                if context.pending_logs:
                    context.battle_log.clear()
                    context.battle_log.append(context.pending_logs.pop(0))
                else:
                    # ログをクリアして待機終了
                    context.battle_log.clear()
            return

        # 2. 行動選択待ち
        if flow.current_phase == BattleFlowComponent.PHASE_INPUT:
            self._handle_action_selection(context, flow, input_comp)

    def _handle_action_selection(self, context, flow, input_comp):
        eid = context.current_turn_entity_id
        if eid is None or eid not in self.world.entities:
            # 異常状態：ターゲットがいないのにInputフェーズ
            flow.current_phase = BattleFlowComponent.PHASE_IDLE
            return

        comps = self.world.entities[eid]
        gauge = comps['gauge']
        part_list = comps['partlist']

        # キー操作
        if input_comp.key_left:
            context.selected_menu_index = (context.selected_menu_index - 1) % 4
        elif input_comp.key_right:
            context.selected_menu_index = (context.selected_menu_index + 1) % 4

        # マウスホバー同期
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

            # チャージ開始（ステータス変更）
            gauge.status, gauge.progress = gauge.CHARGING, 0.0
            
            # ターン終了処理
            context.current_turn_entity_id = None
            
            # フェーズをIDLEに戻す（ゲージ進行再開）
            flow.current_phase = BattleFlowComponent.PHASE_IDLE
            
            # キュー先頭が自分なら削除（Input待ちになった時点で先頭のはず）
            if context.waiting_queue and context.waiting_queue[0] == eid:
                context.waiting_queue.pop(0)