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
    is_cooldown_finished: bool
    should_be_in_queue: bool

class GaugeMechanics:
    """
    ゲージの更新計算、中断判定、待機列への追加判断を行う。
    副作用は持たず、計算結果のみを返す。
    """

    @staticmethod
    def calculate_tick(gauge, dt: float) -> Tuple[float, bool]:
        """
        経過時間に応じた新しい進捗度を計算する。
        
        Returns:
            (new_progress, can_advance)
        """
        can_advance = True
        
        # 状態異常による進行制限チェック
        for effect in gauge.active_effects:
            behavior = StatusRegistry.get(effect.type_id)
            if not behavior.can_charge(effect):
                can_advance = False
                break
        
        if not can_advance:
            return gauge.progress, False

        # ゲージ進行の計算
        new_progress = gauge.progress
        if gauge.status == GaugeStatus.CHARGING:
            new_progress = min(100.0, gauge.progress + (dt / gauge.charging_time * 100.0))
        elif gauge.status == GaugeStatus.COOLDOWN:
            new_progress += (dt / gauge.cooldown_time * 100.0)
            
        return new_progress, True

    @staticmethod
    def get_tick_summary(gauge) -> TickResult:
        """
        現在のゲージ状態のサマリーを返す。
        """
        can_charge = True
        for effect in gauge.active_effects:
            if not StatusRegistry.get(effect.type_id).can_charge(effect):
                can_charge = False
                break

        return TickResult(
            can_charge=can_charge,
            is_cooldown_finished=(gauge.status == GaugeStatus.COOLDOWN and gauge.progress >= 100.0),
            should_be_in_queue=(
                gauge.status == GaugeStatus.ACTION_CHOICE or 
                (gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0)
            )
        )

    @staticmethod
    def get_updated_effects(effects: List[StatusEffect], dt: float) -> List[StatusEffect]:
        """
        状態異常の持続時間を更新し、存続している新しいリストを返す（純粋関数）。
        """
        new_effects = []
        for effect in effects:
            # effect は dataclass なので、System側で値を書き換えるか、ここで複製を作る
            # ここではシンプルに時間を減らした新しいリストを構築する
            new_duration = effect.duration - dt
            if new_duration > 0:
                # 参照を維持したまま時間を更新（副作用をSystemに任せる場合はここも指示だけにするが、
                # StatusEffect自体はECS外のデータなので、ここで更新後のインスタンスを返すのが一般的）
                effect.duration = new_duration
                new_effects.append(effect)
        return new_effects