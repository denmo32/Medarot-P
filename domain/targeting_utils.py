"""ターゲット選定・状態確認に関するユーティリティ関数"""

import random
from typing import List, Optional, Dict, Any, Tuple
from domain.constants import TeamType, PartType
from domain.gauge_logic import calculate_gauge_ratio


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


class TargetingUtils:
    """
    ECS ワールド操作を必要とするターゲット関連ユーティリティ
    
    これらの関数は World インスタンスへのアクセスが必要なため、
    純粋関数ではなくシステム層で使用することを想定しています。
    """

    @staticmethod
    def is_part_alive(world, entity_id: int, part_type: str) -> bool:
        """指定部位が生存しているか（機体が機能停止していないことも含む）"""
        entity_comps = world.try_get_entity(entity_id)
        if not entity_comps:
            return False
        
        defeated = entity_comps.get('defeated')
        if defeated and defeated.is_defeated:
            return False
        
        parts = entity_comps.get('partlist')
        if not parts:
            return False
        
        pid = parts.parts.get(part_type)
        if pid is None:
            return False
        
        p_comps = world.try_get_entity(pid)
        return bool(p_comps and 'health' in p_comps and p_comps['health'].hp > 0)

    @staticmethod
    def get_alive_parts_hp(world, entity_id: int) -> Dict[str, int]:
        """生存している部位名とその HP の辞書を取得"""
        entity_comps = world.try_get_entity(entity_id)
        if not entity_comps or 'partlist' not in entity_comps:
            return {}

        result = {}
        for pt, pid in entity_comps['partlist'].parts.items():
            p_comps = world.try_get_entity(pid)
            if p_comps and 'health' in p_comps:
                hp = p_comps['health'].hp
                if hp > 0:
                    result[pt] = hp
        return result
