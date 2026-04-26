"""アクションの状態遷移・妥当性検証ロジック"""

from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass
from domain.constants import GaugeStatus, ActionType
from battle.mechanics.targeting import TargetingMechanics
from battle.mechanics.log import LogBuilder
from battle.mechanics.trait import TraitRegistry

@dataclass(frozen=True)
class GaugeResetData:
    """ゲージをリセットする際の計算済みパラメータ"""
    status: str
    progress: float
    clear_selection: bool = True

@dataclass(frozen=True)
class ActionInterruptionResult:
    """アクション中断時の判断結果"""
    is_valid: bool
    message: Optional[str] = None
    reset_data: Optional[GaugeResetData] = None

class ActionMechanics:
    """
    アクションに関する判断ロジックと状態更新ヘルパー。
    副作用（コンポーネント書き換え）は持たず、System に適用すべき値を計算して返す。
    """

    @staticmethod
    def get_cooldown_reset_data(current_progress: float, penalty_ratio: float = 1.0) -> GaugeResetData:
        """
        放熱状態へリセットするためのデータを計算する。
        """
        # 充填中断位置から放熱を開始するため、ゲージを反転させる
        if penalty_ratio > 0:
            new_progress = max(0.0, 100.0 - current_progress)
        else:
            new_progress = 0.0

        # NOTE: 放熱中も「我武者羅」などのペナルティ（防御不能）を継続させるため、
        #       どのパーツを使用したか（selected_part）の情報はクリアせずに残す。
        #       完全に放熱が終了して ACTION_CHOICE になる際にクリアされる。
        return GaugeResetData(
            status=GaugeStatus.COOLDOWN,
            progress=new_progress,
            clear_selection=False
        )

    @staticmethod
    def get_choice_reset_data() -> GaugeResetData:
        """
        行動選択状態へリセットするためのデータを計算する。
        """
        return GaugeResetData(
            status=GaugeStatus.ACTION_CHOICE,
            progress=0.0,
            clear_selection=True
        )

    @staticmethod
    def validate_action_continuity(
        gauge_status: str,
        gauge_progress: float,
        gauge_selected_action: str,
        gauge_selected_part: Optional[str],
        gauge_part_targets: Dict[Optional[str], Tuple[int, Optional[str]]],
        actor_name: str,
        is_actor_part_alive: bool,
        is_target_part_alive: bool
    ) -> ActionInterruptionResult:
        """
        アクションの継続妥当性を検証する（充填中・待機中のパーツ破壊チェックなど）。

        Args:
            gauge_status: ゲージ状態（"charging", "cooldown" など）
            gauge_progress: ゲージ進行度（0.0-100.0）
            gauge_selected_action: 選択中のアクション種別
            gauge_selected_part: 選択中のパーツ種別
            gauge_part_targets: パーツごとのターゲット情報 {part_type: (target_id, target_part)}
            actor_name: 実行者の名前
            is_actor_part_alive: 実行予定パーツが生存しているか
            is_target_part_alive: ターゲット部位が生存しているか

        Returns:
            検証結果。is_valid=False の場合は中断が必要。
        """
        # 充填中または行動選択待ち（待機キュー中）のみチェック
        # 放熱中（COOLDOWN）はチェック不要（既に行動が確定していないため）
        if gauge_status not in (GaugeStatus.CHARGING, GaugeStatus.ACTION_CHOICE):
            return ActionInterruptionResult(is_valid=True)

        # 1. 実行予定パーツの生存チェック
        if gauge_selected_action == ActionType.ATTACK and gauge_selected_part:
            if not is_actor_part_alive:
                return ActionInterruptionResult(
                    is_valid=False,
                    message=LogBuilder.get_part_broken_interruption(actor_name),
                    reset_data=ActionMechanics.get_cooldown_reset_data(gauge_progress)
                )

        # 2. ターゲットの生存チェック
        target_data = gauge_part_targets.get(gauge_selected_part)
        if target_data:
            if not is_target_part_alive:
                return ActionInterruptionResult(
                    is_valid=False,
                    message=LogBuilder.get_target_lost(actor_name),
                    reset_data=ActionMechanics.get_cooldown_reset_data(gauge_progress)
                )

        return ActionInterruptionResult(is_valid=True)

    @staticmethod
    def apply_gauge_reset(gauge, reset_data: GaugeResetData) -> None:
        """計算済みのリセットデータをゲージコンポーネントに適用する"""
        gauge.status = reset_data.status
        gauge.progress = reset_data.progress

        if reset_data.clear_selection:
            gauge.selected_action = None
            gauge.selected_part = None
            gauge.part_targets = {}
