"""熟練度（Proficiency）に関するドメインロジック。

メダルの適性Lv（固定）と熟練値（成長）に基づき、威力・成功度への補正値および
経験値獲得によるレベルアップ判定を行う純粋関数群を提供します。
"""
from typing import Tuple
from domain.config import (
    PROFICIENCY_ATTACK_FACTOR,
    PROFICIENCY_SUCCESS_DIVISOR,
    MAX_MASTERY_VALUE,
    EXP_PER_MASTERY_POINT,
)


def calculate_aptitude_attack_bonus(aptitude_level: int) -> int:
    """メダル適性レベル（1〜5）に基づく攻撃力・威力への加算値を計算する。"""
    return max(0, aptitude_level) * PROFICIENCY_ATTACK_FACTOR


def calculate_mastery_success_bonus(mastery_value: int) -> int:
    """熟練値（0〜99）に基づく成功度への加算値を計算する。"""
    return max(0, mastery_value) // PROFICIENCY_SUCCESS_DIVISOR


def gain_mastery_exp(
    current_value: int,
    current_exp: int,
    gain: int = 1,
    exp_per_point: int = EXP_PER_MASTERY_POINT,
    max_value: int = MAX_MASTERY_VALUE,
) -> Tuple[int, int, bool]:
    """経験値を加算し、(新熟練値, 新経験値, レベルアップしたか) のタプルを返す。

    カンスト（MAX_MASTERY_VALUE）到達時は経験値を 0 に固定します。
    """
    if current_value >= max_value:
        return max_value, 0, False

    total_exp = current_exp + gain
    new_value = current_value
    leveled_up = False

    while total_exp >= exp_per_point and new_value < max_value:
        total_exp -= exp_per_point
        new_value += 1
        leveled_up = True

    if new_value >= max_value:
        total_exp = 0

    return new_value, total_exp, leveled_up