"""バトル計算ロジック"""

def calculate_hit_probability(success: int, mobility: int) -> float:
    """
    命中率を計算する（攻撃が回避を上回る確率）
    命中率 = 成功度 / (成功度 + 回避度 * 0.5)
    """
    mobility_weight = 0.5
    denominator = success + (mobility * mobility_weight)
    if denominator <= 0:
        return 1.0
    return success / denominator

def calculate_break_probability(success: int, defense: int) -> float:
    """
    防御突破率を計算する（攻撃が防御を上回る確率）
    突破率 = 成功度 / (成功度 + 防御度 * 0.5)
    """
    defense_weight = 0.5
    denominator = success + (defense * defense_weight)
    if denominator <= 0:
        return 1.0
    return success / denominator

def calculate_damage(base_attack: int, success: int, mobility: int, defense: float, is_critical: bool = False, is_defense: bool = True) -> int:
    """
    ダメージを計算する
    ダメージ = 基本威力 + max(0, 成功度 - 回避度/2 - 防御度/2) / 2
    
    判定による変動:
    1. クリティカル: 回避度・防御度ともに0として計算（防御・回避不能ダメージ）
    2. 防御突破(is_defense=False): 防御度を0として計算（クリーンヒット）
    3. 防御成功(is_defense=True): 回避度・防御度の両方を減算に含める（ガード）
    """
    
    if is_critical:
        # 回避も防御も無視
        mob_val = 0
        def_val = 0
    elif not is_defense:
        # 回避は受けるが、防御（突破済み）は無視
        mob_val = mobility
        def_val = 0
    else:
        # 回避も防御（ガード成功）も受ける
        mob_val = mobility
        def_val = defense
    
    bonus = max(0, success - (mob_val / 2) - (def_val / 2)) / 2
    damage = int(base_attack + bonus)
    
    return damage