"""バトル計算ロジック"""

def calculate_hit_probability(success: int, mobility: int) -> float:
    """
    命中率を計算する
    命中率 = 成功度 / (成功度 + 回避度 * 係数)
    """
    mobility_weight = 0.25
    denominator = success + (mobility * mobility_weight)
    if denominator <= 0:
        return 1.0
    return success / denominator

def calculate_defense_probability(success: int, defense: float) -> float:
    """
    防御発生率を計算する
    防御成功率 = 防御度 / (成功度 + 防御度)
    """
    denominator = success + defense
    if denominator <= 0:
        return 0.0
    return defense / denominator

def calculate_damage(base_attack: int, success: int, mobility: int, defense: float) -> int:
    """
    ダメージを計算する
    ダメージ = 基本威力 + max(0, 成功度 - 回避度/2 - 防御度/2)
    """
    bonus = max(0, success - (mobility / 2) - (defense / 2))
    return int(base_attack + bonus)
