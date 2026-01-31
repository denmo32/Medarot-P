"""ATBゲージ進行と状態異常に関するロジック"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
from domain.constants import GaugeStatus
from battle.mechanics.status import StatusRegistry
from components.battle_component import StatusEffect

@dataclass(frozen=True)
class TickResult:
    """ゲージ更新の結果"""
    can_charge: bool
    new_progress: float
    is_cooldown_finished: bool
    should_be_in_queue: bool

class GaugeMechanics:
    """
    ゲージの更新計算、中断判定、待機列への追加判断を行う。
    副作用は持たず、計算結果のみを返す。
    """

    @staticmethod
    def calculate_tick(gauge, dt: float) -> TickResult:
        """
        経過時間に応じた新しい状態を計算する。
        """
        can_advance = True
        
        # 状態異常による進行制限チェック
        for effect in gauge.active_effects:
            behavior = StatusRegistry.get(effect.type_id)
            if not behavior.can_charge(effect):
                can_advance = False
                break
        
        # ゲージ進行の計算
        new_progress = gauge.progress
        if can_advance:
            if gauge.status == GaugeStatus.CHARGING:
                new_progress = min(100.0, gauge.progress + (dt / gauge.charging_time * 100.0))
            elif gauge.status == GaugeStatus.COOLDOWN:
                new_progress += (dt / gauge.cooldown_time * 100.0)
            
        # 判定
        is_cooldown_finished = (gauge.status == GaugeStatus.COOLDOWN and new_progress >= 100.0)
        should_be_in_queue = (
            gauge.status == GaugeStatus.ACTION_CHOICE or 
            (gauge.status == GaugeStatus.CHARGING and new_progress >= 100.0)
        )

        return TickResult(
            can_charge=can_advance,
            new_progress=new_progress,
            is_cooldown_finished=is_cooldown_finished,
            should_be_in_queue=should_be_in_queue
        )

    @staticmethod
    def get_updated_effects(effects: List[StatusEffect], dt: float) -> List[StatusEffect]:
        """
        状態異常の持続時間を更新し、存続している新しいリストを返す（純粋関数）。
        """
        new_effects = []
        for effect in effects:
            new_duration = effect.duration - dt
            if new_duration > 0:
                effect.duration = new_duration
                new_effects.append(effect)
        return new_effects