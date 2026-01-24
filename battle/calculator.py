"""バトル計算ロジック（純粋関数群）"""

import random

# 計算用定数
MOBILITY_WEIGHT = 0.2       # 回避率計算時の機動性の重み
DEFENSE_WEIGHT = 2          # 突破率計算時の防御力の重み
CRITICAL_THRESHOLD = 2      # クリティカル発生閾値（命中率+突破率）
DAMAGE_PENALTY_DIVISOR = 2  # ダメージボーナス計算時の除数

def calculate_hit_probability(success: int, mobility: int) -> float:
    """
    命中率を計算する（攻撃が回避を上回る確率）
    式: 命中率 = 成功度 / (成功度 + 回避度 * MOBILITY_WEIGHT)
    """
    denominator = success + (mobility * MOBILITY_WEIGHT)
    if denominator <= 0:
        return 1.0
    return success / denominator

def calculate_break_probability(success: int, defense: int) -> float:
    """
    防御突破率を計算する（攻撃が防御を上回る確率）
    式: 突破率 = 成功度 / (成功度 + 防御度 * DEFENSE_WEIGHT)
    """
    denominator = success + (defense * DEFENSE_WEIGHT)
    if denominator <= 0:
        return 1.0
    return success / denominator

def check_is_hit(hit_prob: float) -> bool:
    """命中したかどうかを判定"""
    return random.random() < hit_prob

def check_attack_outcome(hit_prob: float, break_prob: float) -> tuple[bool, bool]:
    """
    攻撃の結果詳細（クリティカル、防御成功）を判定する。
    Returns: (is_critical, is_defense)
    """
    is_break_success = (random.random() < break_prob)
    is_defense = not is_break_success
    
    is_critical = False
    if not is_defense:
        if (hit_prob + break_prob) > CRITICAL_THRESHOLD:
            is_critical = True
            
    return is_critical, is_defense

def calculate_damage(base_attack: int, success: int, mobility: int, defense: float, 
                    is_critical: bool, is_defense: bool) -> int:
    """
    ダメージ計算を行う
    基本式: ダメージ = 基本威力 + ボーナス
    ボーナス = max(0, 成功度 - (ペナルティ)) / 2
    """
    
    if is_critical:
        # クリティカル：相手のステータスを無視
        penalty_mobility = 0
        penalty_defense = 0
    elif not is_defense:
        # 防御突破（クリーンヒット）：防御値を無視
        penalty_mobility = mobility
        penalty_defense = 0
    else:
        # 防御成功（ガード）：全てのステータスで減算
        penalty_mobility = mobility
        penalty_defense = defense
    
    performance_diff = success - (penalty_mobility / DAMAGE_PENALTY_DIVISOR) - (penalty_defense / DAMAGE_PENALTY_DIVISOR)
    bonus_damage = max(0, performance_diff) / 2
    
    final_damage = int(base_attack + bonus_damage)
    return final_damage