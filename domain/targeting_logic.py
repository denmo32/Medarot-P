"""ターゲット選定・状態確認の純粋ロジック"""

import random
from typing import List, Optional, Dict, Tuple
from domain.constants import PartType
from domain.gauge_logic import calculate_gauge_ratio

def is_action_target_valid(
    is_entity_alive: bool,
    is_part_alive: bool,
    target_id: Optional[int],
    target_part: Optional[str] = None
) -> bool:
    """エンティティおよび指定部位が有効（生存）か一括チェック"""
    if target_id is None:
        return False
    if not is_entity_alive:
        return False
    if target_part:
        return is_part_alive
    return True

def get_random_alive_part(alive_parts_hp: Dict[str, int], rng: Optional[random.Random] = None) -> Optional[str]:
    """生存パーツからランダムに部位を選択"""
    if not alive_parts_hp:
        return None
    source = rng if rng else random
    return source.choice(list(alive_parts_hp.keys()))

def get_closest_target_by_gauge(
    enemy_gauge_data: List[Tuple[int, str, float]]
) -> Optional[int]:
    """最もゲージが進んでいる（中央に近い）敵を取得"""
    if not enemy_gauge_data:
        return None
    
    best_target, max_ratio = None, float('-inf')
    
    for enemy_id, status, progress in enemy_gauge_data:
        ratio = calculate_gauge_ratio(status, progress)
        if ratio > max_ratio:
            max_ratio, best_target = ratio, enemy_id
    
    return best_target

def resolve_hit_part(
    part_hps: Dict[str, int], 
    desired_part: Optional[str], 
    is_defense: bool,
    rng: Optional[random.Random] = None
) -> str:
    """被弾部位を決定するポリシー"""
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

    source = rng if rng else random
    return source.choice(list(part_hps.keys()))
