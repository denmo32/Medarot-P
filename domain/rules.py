"""ゲームの基本ルール（勝敗判定など）を定義する純粋関数群"""

from typing import Optional, Sequence, Tuple
from domain.constants import TeamType
from domain.models import RobotSnapshot


def check_battle_end(robots_status: Sequence[RobotSnapshot]) -> Tuple[bool, Optional[TeamType]]:
    """
    現在の機体状況（RobotSnapshot一覧）からバトルの終了判定を行う。
    """
    alive_leaders = {r.team for r in robots_status if r.is_leader and r.is_alive}

    if TeamType.PLAYER not in alive_leaders:
        return True, TeamType.ENEMY
    if TeamType.ENEMY not in alive_leaders:
        return True, TeamType.PLAYER

    return False, None