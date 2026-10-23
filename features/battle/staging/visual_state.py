"""ロボットの視覚的な状態（HPアニメーション・破壊フェードなど）を管理するクラス"""
from typing import Dict, List, TYPE_CHECKING
from domain.constants import PartType

if TYPE_CHECKING:
    from ..entities.robot import Robot


class RobotVisualState:
    """ロボットの視覚的な状態（アニメーションなど）を管理するクラス"""

    def __init__(self, robot: 'Robot'):
        self.robot = robot
        parts_hp = robot.get_parts_hp()

        # 各パーツの表示用HP（現在描画されている値）
        self.parts_display_hp: Dict[PartType, float] = {
            pt: float(hp) for pt, hp in parts_hp.items()
        }
        # 各パーツのアニメーション目標HP
        self.parts_target_hp: Dict[PartType, float] = {
            pt: float(hp) for pt, hp in parts_hp.items()
        }
        # 各パーツのグレーアウト進捗 (0.0: 生存色 ~ 1.0: 破壊色)
        self.parts_break_progress: Dict[PartType, float] = {
            pt: 0.0 if hp > 0 else 1.0 for pt, hp in parts_hp.items()
        }
        # 多段階演出用（貫通など）の目標HPキュー: [{部位: 目標HP}, ...]
        self._pending_step_targets: List[Dict[PartType, float]] = []

    def stage_damage_steps(self, steps: List[Dict[PartType, float]]):
        """ダメージ演出ステップを登録し、第1段階を開始する"""
        self._pending_step_targets = list(steps)
        self.advance_damage_step()

    def advance_damage_step(self):
        """次の演出ステップの目標HPを反映する"""
        if self._pending_step_targets:
            next_targets = self._pending_step_targets.pop(0)
            for pt, target_hp in next_targets.items():
                self.parts_target_hp[pt] = target_hp
        else:
            self.sync_all_targets()

    def sync_all_targets(self):
        """全パーツの目標HPをモデルの現在値に同期する（演出完了時・スキップ時）"""
        self._pending_step_targets.clear()
        for pt, hp in self.robot.get_parts_hp().items():
            self.parts_target_hp[pt] = float(hp)

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
        """いずれかのパーツの表示用HPが目標HPに追いついていないか、またはグレーアウト進行中か"""
        for pt in self.parts_target_hp:
            target_hp = self.parts_target_hp.get(pt, 0.0)
            if self.parts_display_hp.get(pt, 0.0) != target_hp:
                return True
            target_progress = 1.0 if target_hp <= 0 else 0.0
            if self.parts_break_progress.get(pt, 0.0) != target_progress:
                return True
        return False

    def update(self, dt: float):
        """表示用HPの遅延減少アニメーションおよび破壊部位のフェード"""
        for pt in list(self.parts_target_hp.keys()):
            target_hp = self.parts_target_hp.get(pt, 0.0)
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
                fade_speed = 3.5  # 約0.28秒でフェード完了
                if current_progress < target_progress:
                    self.parts_break_progress[pt] = min(
                        target_progress, current_progress + fade_speed * dt
                    )
                else:
                    self.parts_break_progress[pt] = max(
                        target_progress, current_progress - fade_speed * dt
                    )