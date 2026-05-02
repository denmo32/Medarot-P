"""ゲージ計算や時間計算に関連する純粋な計算ロジック"""

import math
from typing import List, Tuple, Optional
from dataclasses import dataclass, replace
from domain.constants import GaugeStatus
from domain.models import StatusEffect
from domain.status_logic import get_status_behavior

@dataclass(frozen=True)
class TickResult:
    """ゲージ更新の結果"""
    can_advance: bool
    new_progress: float
    is_cooldown_finished: bool
    should_be_in_queue: bool

def calculate_action_times(attack_power: int) -> tuple:
    """攻撃力に基づいて充填時間と放熱時間を計算（対数スケール）"""
    base_time = 1
    log_modifier = math.log10(attack_power) if attack_power > 0 else 0

    # 攻撃力が高いほど時間がかかる
    charging_time = base_time + log_modifier
    cooldown_time = base_time + log_modifier

    return charging_time, cooldown_time

def calculate_gauge_ratio(status: str, progress: float) -> float:
    """現在の状態と進捗から、中央への到達度（ポジションレシオ 0.0 ~ 1.0）を計算する。"""
    if status == GaugeStatus.EXECUTING:
        return 1.0
    if status == GaugeStatus.CHARGING:
        return max(0.0, min(1.0, progress / 100.0))
    if status == GaugeStatus.COOLDOWN:
        return max(0.0, min(1.0, 1.0 - (progress / 100.0)))
    return 0.0

def calculate_tick(
    status: str, 
    progress: float, 
    charging_time: float, 
    cooldown_time: float, 
    active_effects: List[StatusEffect], 
    dt: float
) -> TickResult:
    """経過時間に応じた新しい状態を計算する。"""
    can_advance = True

    # 状態異常による進行制限チェック
    for effect in active_effects:
        behavior = get_status_behavior(effect.type_id)
        if not behavior.can_charge(effect):
            can_advance = False
            break

    # ゲージ進行の計算
    new_progress = progress
    if can_advance:
        if status == GaugeStatus.CHARGING:
            new_progress = min(100.0, progress + (dt / charging_time * 100.0))
        elif status == GaugeStatus.COOLDOWN:
            new_progress += (dt / cooldown_time * 100.0)

    # 判定
    is_cooldown_finished = (status == GaugeStatus.COOLDOWN and new_progress >= 100.0)
    should_be_in_queue = (
        status == GaugeStatus.ACTION_CHOICE or 
        (status == GaugeStatus.CHARGING and new_progress >= 100.0)
    )

    return TickResult(
        can_advance=can_advance,
        new_progress=new_progress,
        is_cooldown_finished=is_cooldown_finished,
        should_be_in_queue=should_be_in_queue
    )

def get_updated_effects(effects: List[StatusEffect], dt: float) -> List[StatusEffect]:
    """状態異常の持続時間を更新し、存続している新しいリストを返す。"""
    new_effects = []
    for effect in effects:
        new_duration = effect.duration - dt
        if new_duration > 0:
            new_effects.append(replace(effect, duration=new_duration))
    return new_effects