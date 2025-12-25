"""入力処理システム"""

from core.ecs import System
from config import GAME_PARAMS
from components.battle import GaugeComponent, PartHealthComponent

class InputSystem(System):
    """
    ユーザー入力を処理し、UI状態遷移や行動選択を行うシステム。
    UIのボタン判定ロジックもここに含まれる（Logic Layer）。
    """
    def update(self, dt: float = 0.016):
        # 入力コンポーネントの取得
        inputs = self.world.get_entities_with_components('input')
        if not inputs: return
        input_comp = inputs[0][1]['input']

        # バトルコンテキストの取得
        contexts = self.world.get_entities_with_components('battlecontext')
        if not contexts: return
        context = contexts[0][1]['battlecontext']

        # エスケープキーでゲーム終了（メインループ側でハンドリングされるが、状態フラグとして監視も可能）
        # ここではクリックイベントを中心に処理する

        if not input_comp.mouse_clicked:
            return

        mouse_x = input_comp.mouse_x
        mouse_y = input_comp.mouse_y

        # 1. ゲームオーバー時の処理
        if context.game_over:
            # 入力待ちはMain側でESCキー監視しているため、ここでは何もしない、またはクリックでリセット等の処理
            return

        # 2. メッセージ送り待ち（クリックで次へ）
        if context.waiting_for_input:
            context.waiting_for_input = False
            # ログ表示が溜まりすぎないようにクリアする等の処理があればここで行う
            if len(context.battle_log) > 0:
                # ログを全消去するか、古いものを消すかは仕様次第。
                # 既存仕様ではログクリアイベントが呼ばれていた。
                context.battle_log.clear()
            return

        # 3. 行動選択待ち（ボタン判定）
        if context.waiting_for_action:
            self._handle_action_selection(context, mouse_x, mouse_y)

    def _handle_action_selection(self, context, mouse_x, mouse_y):
        """行動選択ボタンのクリック判定と処理"""
        eid = context.current_turn_entity_id
        if eid is None or eid not in self.world.entities:
            # 異常状態：ターン保持者がいないのに待機中
            context.waiting_for_action = False
            return

        comps = self.world.entities[eid]
        gauge_comp = comps.get('gauge')
        hp_comp = comps.get('parthealth')

        # レイアウト定数（config.pyと合わせる必要あり）
        window_y = GAME_PARAMS['MESSAGE_WINDOW_Y']
        window_height = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        padding = GAME_PARAMS['MESSAGE_WINDOW_PADDING']
        button_y = window_y + window_height - 60
        button_width = 80
        button_height = 40
        button_padding = 10

        # 各ボタンのX座標計算
        head_x = padding
        r_arm_x = padding + button_width + button_padding
        l_arm_x = padding + (button_width + button_padding) * 2
        skip_x = padding + (button_width + button_padding) * 3

        selected_action = None
        selected_part = None

        # 判定用ヘルパー
        def is_clicked(bx, by, bw, bh):
            return bx <= mouse_x <= bx + bw and by <= mouse_y <= by + bh

        if is_clicked(head_x, button_y, button_width, button_height):
            if hp_comp.head_hp > 0:
                selected_action = "attack"
                selected_part = "head"
        elif is_clicked(r_arm_x, button_y, button_width, button_height):
            if hp_comp.right_arm_hp > 0:
                selected_action = "attack"
                selected_part = "right_arm"
        elif is_clicked(l_arm_x, button_y, button_width, button_height):
            if hp_comp.left_arm_hp > 0:
                selected_action = "attack"
                selected_part = "left_arm"
        elif is_clicked(skip_x, button_y, button_width, button_height):
            selected_action = "skip"

        # アクションが決定された場合
        if selected_action:
            gauge_comp.selected_action = selected_action
            gauge_comp.selected_part = selected_part
            
            # 状態遷移
            gauge_comp.status = GaugeComponent.CHARGING
            gauge_comp.progress = 0.0
            
            # コンテキスト更新
            context.current_turn_entity_id = None
            context.waiting_for_action = False
            
            # 待機キューから削除（先頭にいるはず）
            if context.waiting_queue and context.waiting_queue[0] == eid:
                context.waiting_queue.pop(0)
