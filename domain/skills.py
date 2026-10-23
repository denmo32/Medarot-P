# domain/skills.py
"""3層「Skill（技・能力）」のデータ駆動型振る舞いロジック。

技の対象（TargetRule）、選定時期（TargetTiming）、命中方式（HitPolicy）、
演出（SkillPresentation）、および効果（Resolver）を一元管理する。
"""
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Union

from domain.constants import (
    HitPolicy,
    SkillKind,
    SkillPresentation,
    TargetRule,
    TargetTiming,
    SkillType,
)
from domain.effects import (
    resolve_block_effect,
    resolve_protect_effect,
    resolve_repair_effect,
    resolve_restore_effect,
    resolve_scan_effect,
    resolve_stop_effect,
    resolve_trap_effect,
)
from domain.models import ActionResult, EffectResolutionContext


@dataclass(frozen=True)
class SkillDefinition:
    """3層 Skill：技の仕様を定義するデータクラス"""
    skill_kind: SkillKind = SkillKind.ATTACK
    # 射撃・格闘は行動形式側で確定するため None。非攻撃系の技のみ定義する。
    target_timing: Optional[TargetTiming] = None
    target_rule: Optional[TargetRule] = None
    hit_policy: HitPolicy = HitPolicy.STANDARD
    can_pierce: bool = False  # 貫通特性（非頭部破壊時の余剰ダメージを波及させるか）
    presentation: SkillPresentation = SkillPresentation.CUTIN
    targets_part: bool = True
    effect_resolver: Optional[Callable[[EffectResolutionContext], ActionResult]] = None
    is_implemented: bool = True

    def resolve_effect(self, context: EffectResolutionContext) -> ActionResult:
        """非攻撃（効果）行動の解決。リゾルバ未定義なら失敗を返す。"""
        if self.effect_resolver is None:
            return ActionResult(success=False, skill=context.skill)
        return self.effect_resolver(context)


# 全技カタログ（SkillType 全メンバーを網羅。新技はここに追記するだけ）
SKILL_DEFINITIONS: Dict[SkillType, SkillDefinition] = {
    # === 射撃・格闘系の技（ターゲットは行動形式側で確定済み → 指定不要） ===
    SkillType.RIFLE: SkillDefinition(),
    SkillType.GATLING: SkillDefinition(),
    SkillType.MISSILE: SkillDefinition(
        hit_policy=HitPolicy.NEVER_MISS,
        can_pierce=True,
    ),
    SkillType.SWORD: SkillDefinition(),
    SkillType.HAMMER: SkillDefinition(),

    # === 制御系の技（妨害・支援） ===
    SkillType.THUNDER: SkillDefinition(
        skill_kind=SkillKind.EFFECT,
        target_timing=TargetTiming.ON_CHARGE,
        target_rule=TargetRule.ENEMY_BY_PERSONALITY,
        targets_part=True,
        presentation=SkillPresentation.LOG_ONLY,
        effect_resolver=resolve_stop_effect,
    ),
    SkillType.STUN: SkillDefinition(
        skill_kind=SkillKind.EFFECT,
        target_timing=TargetTiming.ON_EXECUTE,
        target_rule=TargetRule.CLOSEST_ENEMY,
        targets_part=True,
        presentation=SkillPresentation.LOG_ONLY,
        effect_resolver=resolve_stop_effect,
    ),
    SkillType.SCAN: SkillDefinition(
        skill_kind=SkillKind.EFFECT,
        target_timing=TargetTiming.NONE,
        target_rule=TargetRule.SELF,
        targets_part=False,
        hit_policy=HitPolicy.AUTO_HIT,
        presentation=SkillPresentation.LOG_ONLY,
        effect_resolver=resolve_scan_effect,
    ),

    # === 防護系の技（護衛・自衛） ===
    SkillType.BLOCK: SkillDefinition(
        skill_kind=SkillKind.EFFECT,
        target_timing=TargetTiming.NONE,
        target_rule=TargetRule.SELF,
        targets_part=False,
        hit_policy=HitPolicy.AUTO_HIT,
        presentation=SkillPresentation.LOG_ONLY,
        effect_resolver=resolve_block_effect,
    ),
    SkillType.PROTECT: SkillDefinition(
        skill_kind=SkillKind.EFFECT,
        target_timing=TargetTiming.NONE,
        target_rule=TargetRule.SELF,
        targets_part=False,
        hit_policy=HitPolicy.AUTO_HIT,
        presentation=SkillPresentation.LOG_ONLY,
        effect_resolver=resolve_protect_effect,
    ),

    # === 設置系の技（掛罠・供給） ===
    SkillType.SHOOTING_TRAP: SkillDefinition(
        skill_kind=SkillKind.EFFECT,
        target_timing=TargetTiming.NONE,
        target_rule=TargetRule.ENEMY_RANDOM,
        targets_part=False,
        hit_policy=HitPolicy.AUTO_HIT,
        presentation=SkillPresentation.LOG_ONLY,
        effect_resolver=resolve_trap_effect,
    ),
    SkillType.COOL_PLANT: SkillDefinition(
        is_implemented=False,
    ),

    # === 救護系の技（修復・復元） ===
    SkillType.REPAIR: SkillDefinition(
        skill_kind=SkillKind.EFFECT,
        target_timing=TargetTiming.ON_CHARGE,
        target_rule=TargetRule.FRIEND_LEAST_HP,
        targets_part=False,
        hit_policy=HitPolicy.AUTO_HIT,
        presentation=SkillPresentation.LOG_ONLY,
        effect_resolver=resolve_repair_effect,
    ),
    SkillType.RESTORE: SkillDefinition(
        skill_kind=SkillKind.EFFECT,
        target_timing=TargetTiming.ON_CHARGE,
        target_rule=TargetRule.FRIEND_ANY_BROKEN,
        targets_part=False,
        hit_policy=HitPolicy.AUTO_HIT,
        presentation=SkillPresentation.LOG_ONLY,
        effect_resolver=resolve_restore_effect,
    ),
}

_UNKNOWN_SKILL = SkillDefinition(is_implemented=False)


def get_skill_definition(skill: Union[SkillType, str, None]) -> SkillDefinition:
    """技に対応する定義を取得する（未定義・未登録なら未実装の技を返す）。"""
    t = SkillType.from_key(skill)
    if t is None:
        return _UNKNOWN_SKILL
    return SKILL_DEFINITIONS.get(t, _UNKNOWN_SKILL)