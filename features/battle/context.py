"""バトルの状態を一元管理するコンテキストクラス（RNG 一元化）"""
import random
from typing import Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING
from domain.constants import PartType, TeamType
from .constants import BattlePhase
from domain.traps import TrapManager
from .models import Robot
from .visual_state import RobotVisualState

if TYPE_CHECKING:
    from .commands import ExecutionReport
    from .cutin_director import CutinDirector


class BattleContext:
    def __init__(self, robots: List[Robot], seed: Optional[int] = None):
        self.robots = robots
        self.visual_states = {r: RobotVisualState(r) for r in robots}

        self.seed = seed if seed is not None else random.randrange(2**32)
        self.rng = random.Random(self.seed)

        self.phase = BattlePhase.INITIAL_SETUP
        self.phase_timer = 0.0
        self.is_opening_done = False

        self._battle_log: List[str] = []
        self.current_actor: Optional[Robot] = None
        self.current_report: Optional['ExecutionReport'] = None
        self.cutin_director: Optional['CutinDirector'] = None  # CutinDirector を保持
        self.preview_targets: Dict[PartType, Optional[Tuple[Robot, Optional[PartType]]]] = {}

        self.winner: Optional[TeamType] = None
        self.result_announced: bool = False
        self.traps = TrapManager()

    # === ログ管理の一元化 ===
    @property
    def battle_log(self) -> Sequence[str]:
        """読み取り専用のバトルログリスト"""
        return self._battle_log

    @property
    def has_log(self) -> bool:
        """ログが存在するか判定"""
        return bool(self._battle_log)

    def set_log(self, messages: Sequence[str]):
        """ログを新しいメッセージ一覧で上書き"""
        self._battle_log = list(messages)

    def append_log(self, message: str):
        """ログに1行追加"""
        self._battle_log.append(message)

    def extend_log(self, messages: Sequence[str]):
        """ログに複数行追加"""
        self._battle_log.extend(messages)

    def clear_log(self):
        """ログをクリア"""
        self._battle_log.clear()