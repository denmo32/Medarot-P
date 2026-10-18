"""熟練度（Proficiency）に関するドメインロジック。

メダルの熟練度データに基づき、成功度や威力への補正値を算出する純粋関数群を提供します。
"""
from typing import Mapping, Optional
from domain.constants import ActionCategory, ActionType, SkillType


def calculate_proficiency_bonus(
    proficiency: Mapping[str, int],
    skill: Optional[SkillType] = None,
    action: Optional[ActionType] = None,
) -> int:
    """技や行動形式に対応する熟練度ボーナス値を計算する。

    熟練度は以下の順で解決されます:
      1. 技名（例: "ライフル"）に直接対応する熟練度
      2. 行動カテゴリ（例: "shooting", "melee"）に対応する熟練度
      3. 未設定時は 0
    """
    if not proficiency:
        return 0

    if skill and skill.value in proficiency:
        return proficiency[skill.value]

    if action:
        category_key = action.category.value
        if category_key in proficiency:
            return proficiency[category_key]

    return 0