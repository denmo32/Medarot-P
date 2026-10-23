"""バトルの状態を一元管理するコンテキストクラス（RNG 一元化・純粋ドメイン状態）。"""
import random
from typing import Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING
from domain.constants import PartType, TeamType
from domain.traps import TrapManager
from .entities.robot import Robot

if TYPE_CHECKING:
    from .entities.commands import ExecutionReport


def find_robot_index(robots: Sequence[Robot], target: Optional[Robot]) -> Optional[int]:
    """ロボットリストから指定されたロボットのインデックスを同一性判定（is）で検索する。"""
    if target is None:
        return None
    for idx, candidate in enumerate(robots):
        if candidate is target:
            return idx
    return None


class BattleContext:
    def __init__(self, robots: List[Robot], seed: Optional[int] = None):
        self.robots = robots

        self.seed = seed if seed is not None else random.randrange(2**32)
        self.rng = random.Random(self.seed)

        self._battle_log: List[str] = []
        self.current_actor: Optional[Robot] = None
        self.current_report: Optional['ExecutionReport'] = None
        self.preview_targets: Dict[PartType, Optional[Tuple[Robot, Optional[PartType]]]] = {}

        self.winner: Optional[TeamType] = None
        self.traps = TrapManager()

    # === ロボット検索 ===
    def find_robot_index(self, robot: Optional[Robot]) -> Optional[int]:
        """管理下のロボットリストから指定機体のインデックスを取得する"""
        return find_robot_index(self.robots, robot)

    # === ログ管理の一元化 ===
    @property
    def battle_log(self) -> Sequence[str]:
        return self._battle_log

    @property
    def has_log(self) -> bool:
        return bool(self._battle_log)

    def set_log(self, messages: Sequence[str]):
        self._battle_log = list(messages)

    def append_log(self, message: str):
        self._battle_log.append(message)

    def extend_log(self, messages: Sequence[str]):
        self._battle_log.extend(messages)

    def clear_log(self):
        self._battle_log.clear()