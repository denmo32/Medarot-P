"""ダメージ計算に関する純粋な計算ロジック"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from domain.combat_formula import calculate_break_probability, check_attack_outcome, calculate_damage
from domain.combat_stats import CombatStats
from components.battle_component import StatusEffect


@dataclass
class CombatResult:
    """戦闘計算の結果"""
    is_hit: bool
    is_critical: bool = False
    is_defense: bool = False
    damage: int = 0
    hit_part: Optional[str] = None
    added_effects: List[StatusEffect] = field(default_factory=list)

    @classmethod
    def miss(cls) -> 'CombatResult':
        """ミス時の結果を生成"""
        return cls(is_hit=False)


@dataclass
class AttackQuality:
    """攻撃の性質（クリティカル・防御）"""
    is_critical: bool
    is_defense: bool


def evaluate_attack_quality(
    success: int,
    tgt_defense: int,
    hit_prob: float,
    prevent_defense: bool,
    force_critical: bool = False
) -> AttackQuality:
    """
    クリティカルか、防御成功かを判定する。
    
    Args:
        success: 攻撃側の成功度
        tgt_defense: 対象の防御力
        hit_prob: 命中確率
        prevent_defense: 防御不能フラグ
        force_critical: 強制クリティカルフラグ
        
    Returns:
        攻撃の性質
    """
    if force_critical:
        return AttackQuality(is_critical=True, is_defense=False)

    break_prob = calculate_break_probability(success, tgt_defense)
    is_critical, is_defense = check_attack_outcome(hit_prob, break_prob)

    # 防御不能ペナルティの適用
    if prevent_defense:
        is_defense = False

    return AttackQuality(is_critical=is_critical, is_defense=is_defense)


def resolve_hit_part(part_hps: Dict[str, int], desired_part: Optional[str], is_defense: bool) -> str:
    """
    被弾部位を決定するポリシー。

    Args:
        part_hps: 生存しているパーツとその HP の辞書
        desired_part: 指定部位
        is_defense: 防御成功フラグ

    Returns:
        被弾した部位の名称 (PartType)
    """
    from domain.constants import PartType
    import random
    
    if not part_hps:
        return PartType.HEAD

    if is_defense:
        # 防御時は、頭部以外の最も HP が高い部位を盾にする
        non_head = [pt for pt in part_hps if pt != PartType.HEAD]
        if non_head:
            # HP の高い順にソート
            sorted_parts = sorted(non_head, key=lambda pt: part_hps[pt], reverse=True)
            return sorted_parts[0]
        return PartType.HEAD

    # ターゲット部位が有効なら優先、そうでなければランダム
    if desired_part in part_hps:
        return desired_part

    # ※ターゲット部位が無効（既に壊れている）な場合はランダムに選択
    return random.choice(list(part_hps.keys()))


def calculate_damage_result(
    attack_trait: str,
    stats: CombatStats,
    hit_prob: float,
    target_part_hps: Dict[str, int],
    target_desired_part: Optional[str],
    prevent_defense: bool,
    force_critical: bool = False
) -> CombatResult:
    """
    命中確定後のダメージ結果を計算する。

    Args:
        attack_trait: 攻撃特性（サンダー等）
        stats: 補正後のステータス
        hit_prob: 命中確率
        target_part_hps: 対象のパーツとその HP の辞書
        target_desired_part: 指定部位
        prevent_defense: 防御不能フラグ
        force_critical: 強制クリティカルフラグ

    Returns:
        ダメージ計算結果
    """
    # 1. 攻撃性質（クリティカル・防御）の決定
    quality = evaluate_attack_quality(
        stats.success, stats.tgt_defense, hit_prob, prevent_defense, force_critical
    )

    # 2. 被弾部位の決定
    hit_part = resolve_hit_part(target_part_hps, target_desired_part, quality.is_defense)

    # 3. ダメージ計算
    damage = calculate_damage(
        stats.attack, stats.success, stats.tgt_mobility, stats.tgt_defense,
        quality.is_critical, quality.is_defense
    )

    # 4. 特性（サンダー等）による追加効果
    from domain.trait import TraitRegistry
    trait_behavior = TraitRegistry.get(attack_trait)
    added_effects = trait_behavior.get_added_effects(stats.success, stats.tgt_mobility)

    return CombatResult(
        is_hit=True,
        is_critical=quality.is_critical,
        is_defense=quality.is_defense,
        damage=damage,
        hit_part=hit_part,
        added_effects=added_effects
    )
