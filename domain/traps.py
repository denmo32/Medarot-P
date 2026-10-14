"""トラップに関する純粋ドメインロジック"""
from dataclasses import dataclass
from typing import Optional, List, Union
from domain.constants import SkillType, ActionCategory, ActionType, TeamType

TRAP_TRIGGER_MAP = {
    SkillType.SHOOTING_TRAP: ActionCategory.SHOOTING,
}


@dataclass(frozen=True)
class InstalledTrap:
    """フィールドに設置されたトラップ情報"""
    skill: SkillType      # 技（SkillType.SHOOTING_TRAP 等）
    target_team: TeamType # 対象チーム (TeamType.PLAYER / ENEMY)
    source_name: str      # 設置者の名前
    damage: int           # 威力


def get_action_category(action: Union[ActionType, str, None]) -> Optional[ActionCategory]:
    st = ActionType.from_key(action)
    return st.category if st else None


def is_trap_triggered(
    trap_skill: Union[SkillType, str], action: Union[ActionType, str, None]
) -> bool:
    """設置された技と実行される行動形式が発動条件を満たすか（Enum ベースで判定）"""
    tt = SkillType.from_key(trap_skill)
    if tt is None:
        return False
    target_category = TRAP_TRIGGER_MAP.get(tt)
    if target_category is None:
        return False
    return get_action_category(action) == target_category


class TrapManager:
    """フィールド上のトラップの追加・消費を一元管理するクラス"""

    def __init__(self, initial_traps: Optional[List[InstalledTrap]] = None):
        self.traps: List[InstalledTrap] = list(initial_traps) if initial_traps else []

    def install(self, trap: InstalledTrap):
        """同一チーム・同一技のトラップを上書き更新"""
        self.traps = [t for t in self.traps if not (t.target_team == trap.target_team and t.skill == trap.skill)]
        self.traps.append(trap)

    def trigger(
        self, target_team: TeamType, action: Union[ActionType, str, None]
    ) -> Optional[InstalledTrap]:
        """条件に合致するトラップを1件消費して返す（使い捨て）"""
        for i, trap in enumerate(self.traps):
            if trap.target_team == target_team and is_trap_triggered(trap.skill, action):
                return self.traps.pop(i)
        return None

    def __iter__(self):
        return iter(self.traps)

    def __len__(self):
        return len(self.traps)

