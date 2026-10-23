"""ゲームの基本ルール（勝敗判定など）を定義する純粋関数群"""

from typing import Optional, Sequence, Tuple
from domain.constants import TeamType
from domain.models import CombatantLeaderProtocol


def check_battle_end(combatants: Sequence[CombatantLeaderProtocol]) -> Tuple[bool, Optional[TeamType]]:
    """
    現在の機体状況（リーダー判定が可能なオブジェクト一覧）からバトルの終了判定を行う。
    """
    alive_leaders = {c.team for c in combatants if c.is_leader and c.is_alive}

    if TeamType.PLAYER not in alive_leaders:
        return True, TeamType.ENEMY
    if TeamType.ENEMY not in alive_leaders:
        return True, TeamType.PLAYER

    return False, None