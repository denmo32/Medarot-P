"""AI 戦略と性格の純粋ロジック（データ駆動型性格エンジン・RNG 注入対応）"""

import random
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, TypeVar, Union

from domain.constants import ACTIONABLE_PART_TYPES, PartType, PersonalityType, TacticsType
from domain.models import TargetPartInfo, TacticsContext

T = TypeVar("T")

# 候補パーツ (PartType, TargetPartInfo) からソートキー（昇順：小さいほど高優先）を導出する評価関数型
PartPriorityKeyFn = Callable[[PartType, TargetPartInfo], Any]


def _select_from_candidates(
    candidates: Sequence[Tuple[T, PartType, TargetPartInfo]],
    key_fn: Optional[PartPriorityKeyFn],
    rng: random.Random,
) -> Optional[T]:
    if not candidates:
        return None

    if key_fn is None:
        return rng.choice(candidates)[0]

    pool = list(candidates)
    rng.shuffle(pool)
    pool.sort(key=lambda item: key_fn(item[1], item[2]))

    # 候補を4枠として、緩やかに重みを減衰させる
    base_weights = [0.55, 0.25, 0.15, 0.05]
    count = min(len(pool), len(base_weights))

    top_items = [item[0] for item in pool[:count]]
    weights = base_weights[:count]

    return rng.choices(top_items, weights=weights, k=1)[0]


class Personality:
    """性格ロジックの共通エンジン。評価関数（key_fn）に基づいてターゲットを選定する。"""

    def __init__(
        self,
        personality_type: PersonalityType,
        key_fn: Optional[PartPriorityKeyFn] = None,
        name: str = "",
    ):
        self.personality_type = personality_type
        self.key_fn = key_fn
        self.name = name or personality_type.display_name

    def select_targets(
        self,
        valid_enemy_ids: List[int],
        enemy_parts: Dict[int, Dict[PartType, TargetPartInfo]],
        rng: Optional[random.Random] = None,
    ) -> Dict[PartType, Optional[Tuple[int, PartType]]]:
        """部位別のターゲットを、性格に従って選定する"""
        _rng = rng or random
        target_slots = ACTIONABLE_PART_TYPES

        if not valid_enemy_ids:
            return {pt: None for pt in target_slots}

        # 全敵機体の生存パーツ候補を集約: ((enemy_id, part_type), part_type, info)
        candidates = [
            ((eid, pt), pt, info)
            for eid in valid_enemy_ids
            for pt, info in enemy_parts.get(eid, {}).items()
            if info.is_alive
        ]

        if not candidates:
            return {pt: None for pt in target_slots}

        return {
            slot: _select_from_candidates(candidates, self.key_fn, _rng)
            for slot in target_slots
        }

    def select_target_part(
        self,
        alive_parts: Dict[PartType, TargetPartInfo],
        rng: Optional[random.Random] = None,
    ) -> Optional[PartType]:
        """単一機体の生存パーツの中から性格に従って1部位を選定する（格闘など）"""
        _rng = rng or random
        if not alive_parts:
            return None

        # 単一機体の生存パーツ候補を集約: (part_type, part_type, info)
        candidates = [
            (pt, pt, info)
            for pt, info in alive_parts.items()
            if info.is_alive
        ]

        return _select_from_candidates(candidates, self.key_fn, _rng)


# === 性格カタログ（データ駆動管理テーブル） ===
# 新規性格の追加は、ここでソートキー関数（昇順評価）を定義する
PERSONALITY_DEFINITIONS: Dict[PersonalityType, Personality] = {
    # ランダム: 一様確率で選択
    PersonalityType.RANDOM: Personality(
        PersonalityType.RANDOM,
        key_fn=None,
    ),
    # チェイサー: 脚部（機動降順）最優先、次いで脚部以外（威力昇順）
    PersonalityType.CHASER: Personality(
        PersonalityType.CHASER,
        key_fn=lambda pt, info: (0, -info.mobility) if pt == PartType.LEGS else (1, info.attack),
    ),
    # チャレンジャー: 残りHPが高い順（HP降順）
    PersonalityType.CHALLENGER: Personality(
        PersonalityType.CHALLENGER,
        key_fn=lambda pt, info: -info.hp,
    ),
    # スイーパー: 残りHPが低い順（HP昇順）
    PersonalityType.SWEEPER: Personality(
        PersonalityType.SWEEPER,
        key_fn=lambda pt, info: info.hp,
    ),
    # ストッパー: 威力が高い順（威力降順）
    PersonalityType.STOPPER: Personality(
        PersonalityType.STOPPER,
        key_fn=lambda pt, info: -info.attack,
    ),
}


def get_personality(personality: Union[PersonalityType, str, None]) -> Personality:
    """指定された性格のインスタンスを取得する（未定義は RANDOM にフォールバック）"""
    pt = PersonalityType.from_key(personality)
    return PERSONALITY_DEFINITIONS.get(pt, PERSONALITY_DEFINITIONS[PersonalityType.RANDOM])


# === 戦術（Tactics）ロジック ===

class Tactics(ABC):
    @abstractmethod
    def select_part(
        self,
        valid_parts: List[PartType],
        context: Optional[TacticsContext] = None,
        rng: Optional[random.Random] = None,
    ) -> Optional[PartType]:
        pass


class RandomTactics(Tactics):
    def select_part(
        self,
        valid_parts: List[PartType],
        context: Optional[TacticsContext] = None,
        rng: Optional[random.Random] = None,
    ) -> Optional[PartType]:
        _rng = rng or random
        if not valid_parts:
            return None
        return _rng.choice(valid_parts)


_tactics: Dict[TacticsType, Tactics] = {
    TacticsType.RANDOM: RandomTactics(),
}


def get_tactics(tactics: Union[TacticsType, str, None]) -> Tactics:
    tt = TacticsType.from_key(tactics)
    return _tactics.get(tt, _tactics[TacticsType.RANDOM])