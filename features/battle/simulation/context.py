"""バトルの状態・検索に関する補助モジュール。"""
from typing import Optional, Sequence
from .entities.robot import Robot


def find_robot_index(robots: Sequence[Robot], target: Optional[Robot]) -> Optional[int]:
    """ロボットリストから指定されたロボットのインデックスを同一性判定（is）で検索する。"""
    if target is None:
        return None
    for idx, candidate in enumerate(robots):
        if candidate is target:
            return idx
    return None