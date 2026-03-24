"""ターゲット選定・状態確認ロジック"""

import random
from typing import List, Optional, Dict, Any, Tuple
from domain.constants import TeamType, PartType
from domain.gauge_logic import calculate_gauge_ratio

class TargetingMechanics:
    """エンティティの生存・有効性・クエリに関するユーティリティ"""

    @staticmethod
    def is_action_target_valid(
        is_entity_alive: bool,
        is_part_alive: bool,
        target_id: Optional[int],
        target_part: Optional[str] = None
    ) -> bool:
        """エンティティおよび指定部位が有効（生存）か一括チェック
        
        Args:
            is_entity_alive: ターゲット機体が生存しているか
            is_part_alive: ターゲット部位が生存しているか
            target_id: ターゲット ID
            target_part: ターゲット部位
        
        Returns:
            有効な場合は True
        """
        if target_id is None:
            return False
        if not is_entity_alive:
            return False
        if target_part:
            return is_part_alive
        return True

    @staticmethod
    def get_random_alive_part(alive_parts_hp: Dict[str, int]) -> Optional[str]:
        """生存パーツからランダムに部位を選択
        
        Args:
            alive_parts_hp: 生存しているパーツと HP {part_type: hp}
        
        Returns:
            選択された部位種別
        """
        if not alive_parts_hp:
            return None
        return random.choice(list(alive_parts_hp.keys()))

    @staticmethod
    def get_closest_target_by_gauge(
        enemy_gauge_data: List[Tuple[int, str, float]]
    ) -> Optional[int]:
        """
        最もゲージが進んでいる（中央に近い）敵を取得
        
        Args:
            enemy_gauge_data: 敵のゲージ情報リスト [(enemy_id, status, progress), ...]
        
        Returns:
            最もゲージが進んでいる敵の ID
        """
        if not enemy_gauge_data:
            return None
        
        best_target, max_ratio = None, float('-inf')
        
        for enemy_id, status, progress in enemy_gauge_data:
            ratio = calculate_gauge_ratio(status, progress)
            if ratio > max_ratio:
                max_ratio, best_target = ratio, enemy_id
        
        return best_target

    @staticmethod
    def resolve_hit_part(part_hps: Dict[str, int], desired_part: Optional[str], is_defense: bool) -> str:
        """
        被弾部位を決定するポリシー。

        Args:
            part_hps: 生存しているパーツとその HP の辞書
            desired_part: 指定部位
            is_defense: 防御成功フラグ

        Returns:
            被弾した部位の名称 (PartType)
        """
        if not part_hps:
            return PartType.HEAD

        if is_defense:
            # 防御時は、頭部以外の最も HP が高い部位を盾にする
            non_head = [pt for pt in part_hps if pt != PartType.HEAD]
            if non_head:
                # HP の高い順にソート
                sorted_parts = sorted(non_head, key=lambda pt: part_hps[pt], reverse=True)
                return sorted_parts[0]
            return PartType.HEAD

        # ターゲット部位が有効なら優先、そうでなければランダム
        if desired_part in part_hps:
            return desired_part

        # ※ターゲット部位が無効（既に壊れている）な場合はランダムに選択
        return random.choice(list(part_hps.keys()))
