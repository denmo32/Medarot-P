"""ターゲット選定に関するドメインロジック"""

from typing import List, Optional
from domain.constants import TeamType
from domain.models import RobotSnapshot


def select_closest_enemy(
    actor_team: TeamType,
    robots_data: List[RobotSnapshot]
) -> Optional[int]:
    """
    ATBゲージの進捗が最も中央（実行ライン）に近い敵機体のインデックスを返す。
    主に格闘行動のリアルタイム・ターゲット解決に使用される。

    Args:
        actor_team: 実行側のチーム
        robots_data: 全機体のスナップショットリスト。

    Returns:
        選ばれた敵機体のインデックス。見つからない場合は None。
    """
    enemies = [r for r in robots_data if r.team != actor_team and r.is_alive]
    if not enemies:
        return None

    target = max(enemies, key=lambda r: r.progress)
    return target.index
