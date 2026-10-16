"""バトルの演出進行（HPアニメーション、タイマー、待機チェック）を一元管理するコンポーネント。"""
from typing import Dict, List, Optional, TYPE_CHECKING

from domain.constants import PartType
from .constants import ADVANCEABLE_PHASES, BattlePhase
from .visual_damage import build_damage_visual_steps

if TYPE_CHECKING:
    from .commands import ExecutionReport
    from .context import BattleContext
    from .models import Robot
    from .visual_state import RobotVisualState


class BattlePresentation:
    """戦闘の視覚演出（HP変動アニメーション・演出待機タイマー）および待機状態を一元管理する。

    BattleManager から演出時間やアニメーションの進行といった表示上の低レベルな関心事を分離し、
    進行マネージャに対してシンプルな待機問い合わせインターフェースを提供する。
    """

    def __init__(self, ctx: 'BattleContext'):
        self.ctx = ctx

    @property
    def visual_states(self) -> Dict['Robot', 'RobotVisualState']:
        return self.ctx.visual_states

    @property
    def phase_timer(self) -> float:
        return self.ctx.phase_timer

    def start_phase_timer(self, duration: float):
        """フェーズごとの演出・待機タイマーを開始する"""
        self.ctx.phase_timer = max(0.0, duration)

    def is_timer_active(self) -> bool:
        """演出タイマーが進行中か"""
        return self.ctx.phase_timer > 0.0

    def is_timer_expired(self) -> bool:
        """演出タイマーが終了したか"""
        return self.ctx.phase_timer <= 0.0

    def is_hp_animating(self) -> bool:
        """いずれかの機体の表示用HPまたは破壊フェードがアニメーション中か"""
        return any(vs.is_hp_animating for vs in self.visual_states.values())

    def is_busy(self) -> bool:
        """演出（HPアニメーションまたはタイマー待機）によって進行がブロックされているか"""
        return self.is_hp_animating() or self.is_timer_active()

    def is_waiting_for_advance(self, phase: BattlePhase) -> bool:
        """キー入力・クリックによるメッセージ送り等の進める入力を待機している状態か"""
        if self.is_busy():
            return False
        return phase in ADVANCEABLE_PHASES

    def update(self, dt: float):
        """1フレーム分の演出アニメーションとタイマーを進行させる"""
        for vs in self.visual_states.values():
            vs.update(dt)

        if self.ctx.phase_timer > 0.0:
            self.ctx.phase_timer = max(0.0, self.ctx.phase_timer - dt)

    def stage_damage(self, report: 'ExecutionReport'):
        """行動結果から多段階のHP変動演出を登録する"""
        if report and report.target:
            steps = build_damage_visual_steps(report)
            if steps:
                self.visual_states[report.target].stage_damage_steps(steps)

    def advance_damage_step(self, target: 'Robot'):
        """対象機体の次のダメージステップ演出（貫通ダメージ等）を進行する"""
        if target in self.visual_states:
            self.visual_states[target].advance_damage_step()

    def sync_all_targets(self):
        """全機体の表示目標HPを実機体の現在HPと即座に同期し、演出タイマーをリセットする"""
        for vs in self.visual_states.values():
            vs.sync_all_targets()
        self.ctx.phase_timer = 0.0