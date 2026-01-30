"""ATBゲージ進行と状態異常に関するロジック"""

from typing import List, Tuple, Optional
from domain.constants import GaugeStatus
from battle.mechanics.status import StatusRegistry
from battle.mechanics.action import ActionMechanics

class GaugeMechanics:
    """
    ゲージの更新計算、中断判定、待機列への追加判断を行う。
    副作用は持たず、計算結果のみを返す。
    """

    @staticmethod
    def process_tick(gauge, dt: float) -> bool:
        """
        ゲージ進行と状態異常の更新を計算。
        進行可能な場合は True を返す。
        """
        can_charge = True
        
        # 状態異常の更新（逆順で安全に削除）
        for effect in reversed(gauge.active_effects):
            behavior = StatusRegistry.get(effect.type_id)
            behavior.on_tick(effect, gauge, dt)
            
            if not behavior.can_charge(effect):
                can_charge = False
                
            if effect.duration <= 0:
                gauge.active_effects.remove(effect)
        
        if not can_charge:
            return False

        # ゲージ進行のメインロジック
        if gauge.status == GaugeStatus.CHARGING:
            gauge.progress = min(100.0, gauge.progress + (dt / gauge.charging_time * 100.0))
        elif gauge.status == GaugeStatus.COOLDOWN:
            gauge.progress += (dt / gauge.cooldown_time * 100.0)
            
        return True

    @staticmethod
    def check_cooldown_complete(gauge) -> bool:
        """放熱が完了したか"""
        return gauge.status == GaugeStatus.COOLDOWN and gauge.progress >= 100.0

    @staticmethod
    def should_be_in_waiting_queue(gauge) -> bool:
        """待機列（入力待ち、または充填完了）に入るべき状態か"""
        return (gauge.status == GaugeStatus.ACTION_CHOICE or 
                (gauge.status == GaugeStatus.CHARGING and gauge.progress >= 100.0))

    @staticmethod
    def evaluate_interruption(world, entity_id: int) -> Tuple[bool, Optional[str]]:
        """
        行動の継続妥当性を検証する。
        
        Returns:
            (is_valid, interruption_message)
        """
        # 現状は ActionMechanics に委譲しているが、将来的にゲージ固有の
        # 特殊な中断ルール（衝撃によるゲージ減少など）があればここに記述する
        return ActionMechanics.validate_action_continuity(world, entity_id)