"""ターゲット解決ロジック（TargetResolver パターン）"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, List
from domain.constants import PartType
from domain.gauge_logic import calculate_gauge_ratio
from battle.mechanics.targeting import TargetingMechanics
from battle.mechanics.personality import PersonalityRegistry


class TargetResolver(ABC):
    """ターゲット解決のための戦略インターフェース"""

    @abstractmethod
    def resolve(
        self,
        actor_eid: int,
        selected_part: Optional[str],
        world
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        ターゲットを解決する

        Args:
            actor_eid: 行動主体のエンティティ ID
            selected_part: 選択中のパーツ
            world: ワールドオブジェクト

        Returns:
            (target_id, target_part) のタプル。解決失敗時は (None, None)
        """
        pass


class MeleeTargetResolver(TargetResolver):
    """
    格闘特性用ターゲット解決
    「一番ゲージが進んでいる敵」を狙い、性格に応じて部位を選ぶ
    """

    def resolve(
        self,
        actor_eid: int,
        selected_part: Optional[str],
        world
    ) -> Tuple[Optional[int], Optional[str]]:
        # 敵チームのゲージ情報を収集
        actor_comps = world.try_get_entity(actor_eid)
        if not actor_comps:
            return None, None

        target_team = "enemy" if actor_comps['team'].team_type == "player" else "player"

        enemy_gauge_data: List[Tuple[int, str, float]] = []
        for eid, ecomps in world.get_entities_with_components('team', 'defeated', 'gauge'):
            if ecomps['team'].team_type == target_team and not ecomps['defeated'].is_defeated:
                enemy_gauge_data.append((eid, ecomps['gauge'].status, ecomps['gauge'].progress))

        # 一番ゲージが進んでいる敵を取得
        closest_enemy_id = TargetingMechanics.get_closest_target_by_gauge(enemy_gauge_data)
        if not closest_enemy_id:
            return None, None

        # 性格に基づいて部位を選択
        personality_id = actor_comps['medal'].personality_id
        personality = PersonalityRegistry.get(personality_id)
        alive_parts_hp = TargetingMechanics.get_alive_parts_hp(world, closest_enemy_id)

        if not alive_parts_hp:
            return None, None

        target_part = personality.select_target_part(alive_parts_hp)
        return closest_enemy_id, target_part


class RangedTargetResolver(TargetResolver):
    """
    射撃特性用ターゲット解決
    事前に決定されたパーツターゲットをそのまま返す
    """

    def resolve(
        self,
        actor_eid: int,
        selected_part: Optional[str],
        world
    ) -> Tuple[Optional[int], Optional[str]]:
        # part_targets から取得（既に行動選択フェーズで決定済み）
        actor_comps = world.try_get_entity(actor_eid)
        if not actor_comps or 'gauge' not in actor_comps:
            return None, None

        gauge = actor_comps['gauge']
        target_data = gauge.part_targets.get(selected_part)

        if target_data:
            target_id, target_part = target_data
            # ターゲット部位の生存確認
            is_alive = TargetingMechanics.is_part_alive(world, target_id, target_part)
            if is_alive:
                return target_id, target_part

        return None, None


class DefaultTargetResolver(TargetResolver):
    """
    デフォルトのターゲット解決
    特性がない場合や、予期しない場合のフォールバック
    """

    def resolve(
        self,
        actor_eid: int,
        selected_part: Optional[str],
        world
    ) -> Tuple[Optional[int], Optional[str]]:
        # 実装は状況に応じて変更
        # 現時点では未実装
        return None, None


class TargetResolverFactory:
    """特性に応じた TargetResolver を生成するファクトリ"""

    # 格闘特性のリスト
    MELEE_TRAITS = {"ソード", "サンダー", "ハンマー"}
    # 射撃特性のリスト
    RANGED_TRAITS = {"ライフル", "ガトリング"}

    _resolvers = {
        "melee": MeleeTargetResolver(),
        "ranged": RangedTargetResolver(),
        "default": DefaultTargetResolver(),
    }

    @classmethod
    def get(cls, attack_trait: str) -> TargetResolver:
        """
        特性に応じた TargetResolver を取得する

        Args:
            attack_trait: 攻撃パーツの特性

        Returns:
            適切な TargetResolver インスタンス
        """
        if attack_trait in cls.MELEE_TRAITS:
            return cls._resolvers["melee"]
        elif attack_trait in cls.RANGED_TRAITS:
            return cls._resolvers["ranged"]
        # 特性がない場合や未知の特性はデフォルト
        return cls._resolvers["default"]
