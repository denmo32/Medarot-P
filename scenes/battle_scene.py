"""バトル画面のシーンラッパー"""

import pygame
from battle.battle_orchestrator import BattleEngine
from input.event_manager import EventManager
from data.game_data_manager import GameDataManager
from data.save_data_manager import SaveDataManager
from ui.config import UI_PARAMS, MENU_PART_ORDER
from ui.battle.system import BattleRenderSystem
from ui.battle.visual_systems import HealthAnimationSystem
from ui.battle.ui_hit_tester import UIHitTester
from battle.constants import BattlePhase

class BattleScene:
    """
    バトル画面のクラス。
    
    このクラスは「ビュー層」として、以下の責務を持つ：
    - ユーザー入力（物理座標）を UI 判定して「論理コマンド」に変換
    - ECS ロジック層へのコマンド伝達
    """

    def __init__(self, screen, data_manager: GameDataManager, save_manager: SaveDataManager):
        self.screen = screen
        # ロジックエンジンの初期化（UI パラメータを注入）
        self.battle_engine = BattleEngine(data_manager, save_manager, UI_PARAMS)
        self.world = self.battle_engine.world
        self.view_model = self.battle_engine.view_model

        self.event_manager = EventManager(self.world)

        # UI 系システムの初期化
        self.health_animation_system = HealthAnimationSystem(self.world)
        self.battle_render_system = BattleRenderSystem(self.world, screen, self.view_model)

        self.running = True

    def handle_events(self):
        """
        イベント処理と UI 入力判定。

        マウス座標から UI ボタンの当たり判定を行い、
        InputComponent に「論理コマンド」としてキューイングする。
        """
        # EventManager を通じて Pygame イベントを処理
        running = self.event_manager.handle_events()
        if not running:
            return 'quit'

        input_comp = self.world.entities[self.event_manager.input_entity_id]['input']

        # ESC キーでバトル中断
        if input_comp.btn_menu:
            return 'title'

        # マウスクリックを btn_ok として扱う（全フェーズ共通）
        # これにより InputSystem は btn_ok だけで判定できる
        if self.event_manager.mouse_clicked:
            input_comp.btn_ok = True

        # 現在のフェーズを取得（UI 判定の可否を決定）
        context = self.world.get_component(self.battle_engine.context_entity_id, 'battlecontext')
        flow = self.world.get_component(self.battle_engine.context_entity_id, 'battleflow')

        if context and flow and flow.current_phase == BattlePhase.INPUT:
            # UI 入力処理（INPUT フェーズのみ）
            self._process_ui_input(input_comp, context, flow)

        return None

    def _process_ui_input(self, input_comp, context, flow):
        """
        UI 入力処理：マウス/キーボードによる選択変更と決定を処理する。
        """
        sw, sh = self.screen.get_size()
        screen_size = (sw, sh)

        # Snapshot からボタン数を取得（スキップボタン等を含めた総数）
        # ※ ViewModel.create_snapshot は以前より軽量になっている
        snapshot = self.view_model.create_snapshot(screen_size)
        buttons = snapshot.action_menu.buttons
        if not buttons:
            return

        # 1. マウスによるボタン選択（動的にレイアウトを計算して判定）
        layouts = UIHitTester.calculate_action_menu_layout(len(buttons), screen_size)
        mouse_idx = UIHitTester.hit_test_action_menu(
            self.event_manager.mouse_x,
            self.event_manager.mouse_y,
            layouts
        )
        if mouse_idx is not None:
            input_comp.selected_menu_index = mouse_idx

        # 2. キーボードによる選択変更（ロジックを UIHitTester に委譲）
        current_idx = input_comp.selected_menu_index if input_comp.selected_menu_index is not None else context.selected_menu_index
        input_comp.selected_menu_index = UIHitTester.resolve_navigation(
            current_idx,
            input_comp.btn_up, input_comp.btn_down, input_comp.btn_left, input_comp.btn_right,
            len(buttons) - 1
        )

        # 3. 決定入力（論理コマンドの発行）
        if input_comp.btn_ok or self.event_manager.mouse_clicked:
            idx = input_comp.selected_menu_index
            if idx is not None and idx < len(MENU_PART_ORDER):
                p_type = MENU_PART_ORDER[idx]
                input_comp.action_commands.append(("attack", p_type))
            else:
                input_comp.action_commands.append(("skip", None))

    def update(self, dt):
        """更新処理"""
        # ロジックの更新
        self.battle_engine.update(dt)
        # 視覚的な演出（HP バーのアニメーション等）の更新
        self.health_animation_system.update(dt)

    def render(self):
        """描画処理"""
        # レンダリングシステムの実行
        self.battle_render_system.update(0)
