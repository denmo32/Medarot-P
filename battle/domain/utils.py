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

def calculate_current_x(base_x: int, status: str, progress: float, team_type: str) -> float:
    """エンティティの現在のアイコンX座標を計算する（ゲージ進行に基づく視覚的座標）"""
    center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
    offset = 40
    
    if team_type == TeamType.PLAYER:
        target_x = center_x - offset
        if status == GaugeStatus.CHARGING:
            return base_x + (progress / 100.0) * (target_x - base_x)
        if status == GaugeStatus.EXECUTING:
            return target_x
        if status == GaugeStatus.COOLDOWN:
            return target_x - (progress / 100.0) * (target_x - base_x)
        return base_x
    else:
        start_x = base_x + GAME_PARAMS['GAUGE_WIDTH']
        target_x = center_x + offset
        if status == GaugeStatus.CHARGING:
            return start_x - (progress / 100.0) * (start_x - target_x)
        if status == GaugeStatus.EXECUTING:
            return target_x
        if status == GaugeStatus.COOLDOWN:
            return target_x + (progress / 100.0) * (start_x - target_x)
        return start_x

def get_closest_target_by_gauge(world, my_team_type: str):
    target_team = TeamType.ENEMY if my_team_type == TeamType.PLAYER else TeamType.PLAYER
    best_target = None
    extreme_x = float('inf') if my_team_type == TeamType.PLAYER else float('-inf')
    candidates = world.get_entities_with_components('team', 'defeated', 'position', 'gauge')
    
    for teid, tcomps in candidates:
        if tcomps['team'].team_type == target_team and not tcomps['defeated'].is_defeated:
            cur_x = calculate_current_x(
                tcomps['position'].x, 
                tcomps['gauge'].status, 
                tcomps['gauge'].progress, 
                tcomps['team'].team_type
            )
            if my_team_type == TeamType.PLAYER:
                if cur_x < extreme_x:
                    extreme_x = cur_x
                    best_target = teid
            else:
                if cur_x > extreme_x:
                    extreme_x = cur_x
                    best_target = teid
    return best_target

def reset_gauge_to_cooldown(gauge):
    gauge.status = GaugeStatus.COOLDOWN
    gauge.progress = 0.0
    gauge.selected_action = None
    gauge.selected_part = None

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