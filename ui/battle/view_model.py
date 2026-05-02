"""ECS から Snapshot への変換ロジック（ViewModel のファサード）"""

from typing import Tuple
from battle.constants import BattlePhase
from battle.systems.base.world_accessor import get_battle_state
from .snapshot import BattleStateSnapshot, ActionMenuData
from .builders import FieldSnapshotBuilder, UISnapshotBuilder, CutinSnapshotBuilder

class BattleViewModel:
    """
    各ビルダーを統括し、World の状態を描画用の Snapshot に変換するファサード。

    リファクタリング後：
    - Snapshot 生成時に画面サイズを渡し、レイアウト計算（Rect）も実施
    - Snapshot は「完全な設計図」となり、Renderer/Scene はそれを見るのみ
    """

    def __init__(self, world):
        self.world = world
        self.field_builder = FieldSnapshotBuilder(world)
        self.ui_builder = UISnapshotBuilder(world)
        self.cutin_builder = CutinSnapshotBuilder(world, self.field_builder)

    def create_snapshot(self, screen_size: Tuple[int, int]) -> BattleStateSnapshot:
        """現在の世界の状態を切り出し、Snapshot を生成する"""
        context, flow = get_battle_state(self.world)
        if not context or not flow:
            return BattleStateSnapshot()

        snapshot = BattleStateSnapshot()

        # フィールド・UI・カットインの状態を構築
        snapshot.characters = self.field_builder.build_characters(context, flow)
        snapshot.target_marker_eid = self.field_builder.get_active_target_eid(context, flow)
        snapshot.target_line = self.field_builder.build_target_line(snapshot.characters, flow)

        snapshot.log_window = self.ui_builder.build_log_window(context, flow)
        snapshot.action_menu = self.ui_builder.build_action_menu(context, flow, screen_size)
        snapshot.game_over = self.ui_builder.build_game_over(flow)

        if flow.current_phase == BattlePhase.OPENING_POPUP:
            snapshot.opening_popup_text = "ロボトルファイト！"

        if flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT]:
            snapshot.cutin = self.cutin_builder.build(flow, screen_size)

        return snapshot

    def get_action_menu_data(self, screen_size: Tuple[int, int]) -> ActionMenuData:
        """アクションメニューの情報のみを軽量に取得する"""
        context, flow = get_battle_state(self.world)
        if not context or not flow:
            return ActionMenuData(is_active=False)
        return self.ui_builder.build_action_menu(context, flow, screen_size)
