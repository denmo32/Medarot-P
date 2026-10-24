"""ロボットの視覚的な状態（HPアニメーション・破壊フェードなど）を管理するクラス"""
from typing import Dict, TYPE_CHECKING
from domain.constants import PartType, ALL_PART_TYPES, AccentState, GaugeStatus

if TYPE_CHECKING:
    from ..simulation.entities.robot import Robot


class RobotVisualState:
    """ロボットの視覚的な状態（アニメーションなど）を管理するクラス"""

    def __init__(self, robot: 'Robot'):
        self.robot = robot
        parts_hp = robot.get_parts_hp()

        # 各パーツの表示用HP（現在描画されている値）
        self.parts_display_hp: Dict[PartType, float] = {
            pt: float(hp) for pt, hp in parts_hp.items()
        }
        # 各パーツのグレーアウト進捗 (0.0: 生存色 ~ 1.0: 破壊色)
        self.parts_break_progress: Dict[PartType, float] = {
            pt: 0.0 if hp > 0 else 1.0 for pt, hp in parts_hp.items()
        }

    @property
    def is_visually_alive(self) -> bool:
        """表示上の頭部HPまたは破壊進捗から、視覚的に生存しているかを判定"""
        head_part = self.robot.head
        if head_part is None:
            return False
        head_hp = self.parts_display_hp.get(PartType.HEAD, 0.0)
        head_break = self.parts_break_progress.get(PartType.HEAD, 1.0)
        return head_hp > 0.0 or head_break < 1.0

    @property
    def is_hp_animating(self) -> bool:
        """いずれかのパーツの表示用HPがモデルの実HPに追いついていないか、またはグレーアウト進行中か"""
        for pt in ALL_PART_TYPES:
            current_display = self.parts_display_hp.get(pt, 0.0)
            target_hp = float(self.robot.get_part_hp(pt))
            if current_display != target_hp:
                return True
            target_progress = 1.0 if target_hp <= 0 else 0.0
            if self.parts_break_progress.get(pt, 0.0) != target_progress:
                return True
        return False

    @property
    def accent_state(self) -> AccentState:
        """ロボットの現在の進行状況・生存状態に応じたアクセントカラー状態"""
        if self.robot.is_stopped:
            return AccentState.STOPPED
        if not self.is_visually_alive:
            return AccentState.NEUTRAL
        status = self.robot.gauge_status
        if status == GaugeStatus.CHARGING:
            return AccentState.CHARGING
        if status == GaugeStatus.COOLDOWN:
            return AccentState.COOLDOWN
        if status in (GaugeStatus.READY, GaugeStatus.EXECUTING):
            return AccentState.READY
        return AccentState.NEUTRAL

    def update(self, dt: float):
        """表示用HPの遅延減少アニメーションおよび破壊部位のフェード"""
        for pt in ALL_PART_TYPES:
            target_hp = float(self.robot.get_part_hp(pt))
            current_display = self.parts_display_hp.get(pt, target_hp)

            if current_display != target_hp:
                diff = target_hp - current_display
                if abs(diff) < 0.2:
                    self.parts_display_hp[pt] = target_hp
                    current_display = target_hp
                else:
                    self.parts_display_hp[pt] += diff * 5.0 * dt
                    current_display = self.parts_display_hp[pt]

            if target_hp <= 0:
                is_hp_zero = (current_display <= 0.0 or current_display == target_hp)
                target_progress = 1.0 if is_hp_zero else 0.0
            else:
                target_progress = 0.0

            current_progress = self.parts_break_progress.get(pt, target_progress)

            if current_progress != target_progress:
                fade_speed = 3.5
                if current_progress < target_progress:
                    self.parts_break_progress[pt] = min(
                        target_progress, current_progress + fade_speed * dt
                    )
                else:
                    self.parts_break_progress[pt] = max(
                        target_progress, current_progress - fade_speed * dt
                    )