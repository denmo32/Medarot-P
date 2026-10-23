"""ターゲット選定に関するドメインロジック"""

from typing import Optional, Sequence
from domain.constants import TeamType
from domain.models import CombatantTargetProtocol


def select_closest_enemy(
    actor_team: TeamType,
    combatants: Sequence[CombatantTargetProtocol],
) -> Optional[int]:
    """
    ATBゲージの進捗が最も中央（実行ライン）に近い敵機体のインデックスを返す。
    主に格闘行動のリアルタイム・ターゲット解決に使用される。

    Args:
        actor_team: 実行側のチーム
        combatants: 全機体のリスト（Robot または Snapshot）。

    Returns:
        選ばれた敵機体のインデックス。見つからない場合は None。
    """
    enemies = [
        (idx, c) for idx, c in enumerate(combatants)
        if c.team != actor_team and c.is_alive
    ]
    if not enemies:
        return None

    target_idx, _ = max(enemies, key=lambda pair: pair[1].position)
    return target_idx