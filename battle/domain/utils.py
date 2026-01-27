"""バトル関連のユーティリティ関数"""

import math
from typing import Optional
from config import GAME_PARAMS
from battle.constants import GaugeStatus, TeamType, ActionType, BattlePhase
from battle.domain.targeting import TargetingLogic

def calculate_action_times(attack_power: int) -> tuple:
    """攻撃力に基づいてチャージ時間とクールダウン時間を計算（対数スケール）"""
    base_time = 1
    log_modifier = math.log10(attack_power) if attack_power > 0 else 0
    
    charging_time = base_time + log_modifier
    cooldown_time = base_time + log_modifier
    
    return charging_time, cooldown_time

def transition_to_phase(flow, next_phase: str, timer: float = 0.0):
    """バトルフェーズを遷移させ、タイマー等の関連状態を初期化する"""
    flow.current_phase = next_phase
    flow.phase_timer = timer
    # 特定フェーズへの遷移時に行うリセット処理
    if next_phase == BattlePhase.IDLE:
        flow.processing_event_id = None
        flow.active_actor_id = None
        flow.cutin_progress = 0.0

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
    transition_to_phase(flow, BattlePhase.IDLE)
    
    if context.waiting_queue and context.waiting_queue[0] == eid:
        context.waiting_queue.pop(0)

def calculate_gauge_ratio(status: str, progress: float) -> float:
    """
    現在の状態と進捗から、中央への到達度（ポジションレシオ）を計算する。
    """
    if status == GaugeStatus.EXECUTING:
        return 1.0
    
    if status == GaugeStatus.CHARGING:
        return max(0.0, min(1.0, progress / 100.0))
        
    if status == GaugeStatus.COOLDOWN:
        return max(0.0, min(1.0, 1.0 - (progress / 100.0)))
        
    return 0.0

def calculate_current_x(base_x: int, status: str, progress: float, team_type: str) -> float:
    """エンティティの現在のアイコンX座標を計算する（ゲージ進行に基づく視覚的座標）"""
    center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
    offset = 40
    
    ratio = calculate_gauge_ratio(status, progress)
    
    if team_type == TeamType.PLAYER:
        target_x = center_x - offset
        return base_x + ratio * (target_x - base_x)
    else:
        start_x = base_x + GAME_PARAMS['GAUGE_WIDTH']
        target_x = center_x + offset
        return start_x + ratio * (target_x - start_x)

def get_closest_target_by_gauge(world, my_team_type: str):
    """
    ゲージ進行度に基づいて「最も中央に近い（手前にいる）」ターゲットを選定する。
    """
    target_team = TeamType.ENEMY if my_team_type == TeamType.PLAYER else TeamType.PLAYER
    best_target = None
    max_ratio = float('-inf')
    
    candidates = world.get_entities_with_components('team', 'defeated', 'gauge')
    
    for teid, tcomps in candidates:
        if tcomps['team'].team_type == target_team and not tcomps['defeated'].is_defeated:
            ratio = calculate_gauge_ratio(
                tcomps['gauge'].status, 
                tcomps['gauge'].progress
            )
            if ratio > max_ratio:
                max_ratio = ratio
                best_target = teid
                
    return best_target

def reset_gauge_to_cooldown(gauge):
    """
    行動終了後、クールダウン状態へ移行する。
    """
    gauge.status = GaugeStatus.COOLDOWN
    gauge.progress = 0.0

def interrupt_gauge_return_home(gauge):
    """
    行動を中断し、その位置からホームポジションへ戻る冷却を開始する。
    """
    current_p = gauge.progress
    gauge.status = GaugeStatus.COOLDOWN
    gauge.progress = max(0.0, 100.0 - current_p)
    gauge.selected_action = None
    gauge.selected_part = None

def is_target_valid(world, target_id: Optional[int], target_part: Optional[str] = None) -> bool:
    """
    ターゲットおよび指定部位が攻撃可能な状態か判定する。
    (TargetingLogicへのプロキシ)
    """
    return TargetingLogic.is_action_target_valid(world, target_id, target_part)