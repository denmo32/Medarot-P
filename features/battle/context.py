"""バトルの状態を一元管理するコンテキストクラス（RNG 一元化・純粋ドメイン状態）。"""
import random
from typing import Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING
from domain.constants import PartType, TeamType
from domain.traps import TrapManager
from .entities.robot import Robot

if TYPE_CHECKING:
    from .entities.commands import ExecutionReport


class BattleContext:
    def __init__(self, robots: List[Robot], seed: Optional[int] = None):
        self.robots = robots

        self.seed = seed if seed is not None else random.randrange(2**32)
        self.rng = random.Random(self.seed)

        self.is_opening_done = False

        self._battle_log: List[str] = []
        self.current_actor: Optional[Robot] = None
        self.current_report: Optional['ExecutionReport'] = None
        self.preview_targets: Dict[PartType, Optional[Tuple[Robot, Optional[PartType]]]] = {}

        self.winner: Optional[TeamType] = None
        self.traps = TrapManager()

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