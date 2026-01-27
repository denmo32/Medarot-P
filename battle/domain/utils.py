"""バトル関連のユーティリティ関数"""

import math
from typing import Optional
from config import GAME_PARAMS
from battle.constants import GaugeStatus, TeamType, ActionType, BattlePhase

def calculate_action_times(attack_power: int) -> tuple:
    """攻撃力に基づいてチャージ時間とクールダウン時間を計算（対数スケール）"""
    base_time = 1
    log_modifier = math.log10(attack_power) if attack_power > 0 else 0
    
    charging_time = base_time + log_modifier
    cooldown_time = base_time + log_modifier
    
    return charging_time, cooldown_time

def apply_action_command(world, eid: int, action: str, part: Optional[str]):
    """
    コマンドを適用し、時間計算を行ってチャージを開始する共通関数
    """
    comps = world.entities[eid]
    gauge = comps['gauge']
    context = world.entities[0]['battlecontext']
    flow = world.entities[0]['battleflow']

    gauge.selected_action = action
    gauge.selected_part = part

    if action == ActionType.ATTACK and part:
        part_id = comps['partlist'].parts.get(part)
        p_comps = world.entities[part_id]
        atk_comp = p_comps['attack']
        atk = atk_comp.base_attack
        c_t, cd_t = calculate_action_times(atk)
        
        mod = atk_comp.time_modifier
        gauge.charging_time = c_t * mod
        gauge.cooldown_time = cd_t * mod
        
    gauge.status = GaugeStatus.CHARGING
    gauge.progress = 0.0
    
    context.current_turn_entity_id = None
    flow.current_phase = BattlePhase.IDLE
    
    if context.waiting_queue and context.waiting_queue[0] == eid:
        context.waiting_queue.pop(0)

def calculate_gauge_ratio(status: str, progress: float) -> float:
    """
    現在の状態と進捗から、中央への到達度（ポジションレシオ）を計算する。
    Returns:
        float: 0.0 (ベースポジション) 〜 1.0 (中央ライン)
    """
    if status == GaugeStatus.EXECUTING:
        return 1.0
    
    if status == GaugeStatus.CHARGING:
        # 0% -> 100% で 中央へ近づく (0.0 -> 1.0)
        return max(0.0, min(1.0, progress / 100.0))
        
    if status == GaugeStatus.COOLDOWN:
        # 0% -> 100% で ベースへ戻る (1.0 -> 0.0)
        return max(0.0, min(1.0, 1.0 - (progress / 100.0)))
        
    # ACTION_CHOICE など
    return 0.0

def calculate_current_x(base_x: int, status: str, progress: float, team_type: str) -> float:
    """エンティティの現在のアイコンX座標を計算する（ゲージ進行に基づく視覚的座標）"""
    center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
    offset = 40
    
    # 進行度(0.0~1.0)を取得
    ratio = calculate_gauge_ratio(status, progress)
    
    if team_type == TeamType.PLAYER:
        # プレイヤー: Base(左) -> Target(中央左)
        target_x = center_x - offset
        return base_x + ratio * (target_x - base_x)
    else:
        # エネミー: Base(右) -> Target(中央右)
        # エネミーのbase_xは描画開始位置(左端)だが、ゲージ表示上のStart位置は右端相当
        start_x = base_x + GAME_PARAMS['GAUGE_WIDTH']
        target_x = center_x + offset
        
        # エネミーは Start(Right) -> Target(Left/Center) へ移動
        # ratio 0.0 => Start, ratio 1.0 => Target
        return start_x + ratio * (target_x - start_x)

def get_closest_target_by_gauge(world, my_team_type: str):
    """
    ゲージ進行度に基づいて「最も中央に近い（手前にいる）」ターゲットを選定する。
    ピクセル座標ではなく、正規化された到達度(ratio)で判定を行う。
    """
    target_team = TeamType.ENEMY if my_team_type == TeamType.PLAYER else TeamType.PLAYER
    best_target = None
    
    # 最も中央に近い = ratioが最も大きい
    max_ratio = float('-inf')
    
    candidates = world.get_entities_with_components('team', 'defeated', 'gauge')
    
    for teid, tcomps in candidates:
        if tcomps['team'].team_type == target_team and not tcomps['defeated'].is_defeated:
            ratio = calculate_gauge_ratio(
                tcomps['gauge'].status, 
                tcomps['gauge'].progress
            )
            
            # 中央に近いほど優先（ratioが高いほど優先）
            # 同じratioの場合はエンティティIDなどで安定させることも可能だが、ここではシンプルに
            if ratio > max_ratio:
                max_ratio = ratio
                best_target = teid
                
    return best_target

def reset_gauge_to_cooldown(gauge):
    """
    行動終了後、クールダウン状態へ移行する。
    注意: クールダウン中もスキルのペナルティ判定（我武者羅など）が必要なため、
    selected_action / selected_part はクリアせずに保持する。
    """
    gauge.status = GaugeStatus.COOLDOWN
    gauge.progress = 0.0
    # ここでの selected_action/part のクリアを削除

def interrupt_gauge_return_home(gauge):
    current_p = gauge.progress
    gauge.status = GaugeStatus.COOLDOWN
    gauge.progress = max(0.0, 100.0 - current_p)
    gauge.selected_action = None
    gauge.selected_part = None

def is_target_valid(world, target_id: Optional[int], target_part: Optional[str] = None) -> bool:
    if target_id is None: return False
    t_comps = world.try_get_entity(target_id)
    if not t_comps: return False
    if 'defeated' in t_comps and t_comps['defeated'].is_defeated: return False
    if target_part:
        if 'partlist' not in t_comps: return False
        p_id = t_comps['partlist'].parts.get(target_part)
        if not p_id: return False
        p_comps = world.try_get_entity(p_id)
        if not p_comps or 'health' not in p_comps: return False
        if p_comps['health'].hp <= 0: return False
    return True