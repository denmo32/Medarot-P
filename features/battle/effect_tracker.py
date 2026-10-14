"""機体に付与された戦闘効果（状態異常・バフ）の管理コンポーネント。"""
import dataclasses
from typing import Callable, List, Optional
from domain.constants import EffectType, EffectStackPolicy, PartType
from domain.models import StatusEffect


class EffectTracker:
    """機体の有効な効果リストの保持、時間減算、各種状態の判定を担当"""

    def __init__(self, initial_effects: Optional[List[StatusEffect]] = None):
        self.active_effects: List[StatusEffect] = list(initial_effects) if initial_effects else []

    def add(self, new_effect: StatusEffect):
        """効果の重複ルールに従って追加または更新"""
        existing = next(
            (e for e in self.active_effects if e.type == new_effect.type and e.part_type == new_effect.part_type),
            None
        )
        if existing:
            if new_effect.stack_policy == EffectStackPolicy.REFRESH_MAX:
                if new_effect.duration > existing.duration:
                    self.active_effects.remove(existing)
                    self.active_effects.append(new_effect)
            elif new_effect.stack_policy == EffectStackPolicy.CHARGES_MAX:
                if (new_effect.charges or 0) > (existing.charges or 0):
                    self.active_effects.remove(existing)
                    self.active_effects.append(new_effect)
            elif new_effect.stack_policy == EffectStackPolicy.OVERWRITE:
                self.active_effects.remove(existing)
                self.active_effects.append(new_effect)
            elif new_effect.stack_policy == EffectStackPolicy.STACK:
                self.active_effects.append(new_effect)
        else:
            self.active_effects.append(new_effect)

    def consume_attack_charges(self) -> List[StatusEffect]:
        """攻撃行動に伴い消費される回数制バフを1減算する。"""
        expired: List[StatusEffect] = []
        updated: List[StatusEffect] = []
        for eff in self.active_effects:
            if eff.charges is not None:
                new_charges = eff.charges - 1
                if new_charges <= 0:
                    expired.append(eff)
                else:
                    updated.append(dataclasses.replace(eff, charges=new_charges))
            else:
                updated.append(eff)
        self.active_effects = updated
        return expired

    def clear_stances(self):
        """次回行動実行時に解除される構え（スタンス）効果を一括解除する。"""
        self.active_effects = [eff for eff in self.active_effects if not eff.type.is_stance]

    def update(self, dt: float):
        """効果時間を進行させ、期限切れの効果を破棄"""
        updated = []
        for eff in self.active_effects:
            new_dur = eff.duration - dt
            if new_dur > 0:
                updated.append(dataclasses.replace(eff, duration=new_dur))
        self.active_effects = updated

    def has_effect(self, effect_type: EffectType) -> bool:
        return any(eff.type == effect_type for eff in self.active_effects)

    def is_part_stopped(self, part_type: PartType) -> bool:
        return any(
            eff.type == EffectType.STOP and eff.part_type == part_type
            for eff in self.active_effects
        )

    def is_stopped(self) -> bool:
        return self.is_part_stopped(PartType.LEGS) or any(
            eff.type == EffectType.STOP and eff.part_type is None
            for eff in self.active_effects
        )

    def is_blocking(self) -> bool:
        return self.has_effect(EffectType.BLOCK)

    def get_protect_reduction(self, is_part_alive_fn: Optional[Callable[[PartType], bool]] = None) -> int:
        for eff in self.active_effects:
            if eff.type == EffectType.PROTECT:
                if eff.part_type and is_part_alive_fn:
                    if not is_part_alive_fn(eff.part_type):
                        continue
                return eff.magnitude
        return 0

    def get_buff_success(self) -> int:
        return sum(
            eff.magnitude
            for eff in self.active_effects
            if eff.type == EffectType.SUCCESS_UP
        )