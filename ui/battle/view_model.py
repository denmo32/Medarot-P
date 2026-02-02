"""ECSからSnapshotへの変換ロジック（ViewModelのファサード）"""

from typing import Optional
from battle.constants import BattlePhase
from ui.config import MENU_PART_ORDER
from battle.mechanics.flow import get_battle_state
from .layout_utils import calculate_action_menu_layout
from .snapshot import BattleStateSnapshot
from .builders import FieldSnapshotBuilder, UISnapshotBuilder, CutinSnapshotBuilder
# 画面サイズ取得のためにBaseRenderer相当の機能が必要だが、
# ViewModelはLogic層に近いのでpygameへの直接依存はなるべく避けたい。
# しかしhit_testなどは画面サイズ必須。ここでは初期化時に注入するか、都度取得する。
# 簡易的にpygame.display.get_surface()から取得する。
import pygame

class BattleViewModel:
    """各ビルダーを統括し、Worldの状態を描画用のSnapshotに変換するファサード"""
    
    def __init__(self, world):
        self.world = world
        self.field_builder = FieldSnapshotBuilder(world)
        self.ui_builder = UISnapshotBuilder(world)
        self.cutin_builder = CutinSnapshotBuilder(world, self.field_builder)

    def _get_screen_size(self):
        s = pygame.display.get_surface()
        return s.get_size() if s else (800, 600)

    def create_snapshot(self) -> BattleStateSnapshot:
        """現在の世界の状態を切り出し、Snapshotを生成する"""
        context, flow = get_battle_state(self.world)
        if not context or not flow:
            return BattleStateSnapshot()

        snapshot = BattleStateSnapshot()
        screen_size = self._get_screen_size()
        
        # フィールド・UI・カットインの状態を構築
        snapshot.characters = self.field_builder.build_characters(context, flow)
        snapshot.target_marker_eid = self.field_builder.get_active_target_eid(context, flow)
        snapshot.target_line = self.field_builder.build_target_line(snapshot.characters, flow)
        
        snapshot.log_window = self.ui_builder.build_log_window(context, flow)
        snapshot.action_menu = self.ui_builder.build_action_menu(context, flow)
        snapshot.game_over = self.ui_builder.build_game_over(flow)

        if flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT]:
            snapshot.cutin = self.cutin_builder.build(flow, screen_size)
        
        return snapshot

    def hit_test_action_menu(self, mx: int, my: int) -> Optional[int]:
        """マウス座標がどのボタンにあるかを判定"""
        _, flow = get_battle_state(self.world)
        if not flow or flow.current_phase != BattlePhase.INPUT:
            return None

        # 画面サイズを取得してレイアウトを再計算
        screen_size = self._get_screen_size()
        layout = calculate_action_menu_layout(len(MENU_PART_ORDER) + 1, screen_size)
        
        for i, rect in enumerate(layout):
            if rect.collidepoint(mx, my):
                return i
        return None