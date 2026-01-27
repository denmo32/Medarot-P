"""バトル関連のユーティリティ関数"""

import math
from typing import Optional, Tuple
from config import GAME_PARAMS
from battle.constants import GaugeStatus, TeamType, BattlePhase

def get_battle_state(world) -> Tuple[Optional[any], Optional[any]]:
    """バトル全体の共通コンポーネント(context, flow)を安全に取得する"""
    entities = world.get_entities_with_components('battlecontext', 'battleflow')
    if not entities:
        return None, None
    return entities[0][1]['battlecontext'], entities[0][1]['battleflow']

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
    if next_phase == BattlePhase.IDLE:
        flow.processing_event_id = None
        flow.active_actor_id = None
        flow.cutin_progress = 0.0

def calculate_gauge_ratio(status: str, progress: float) -> float:
    """現在の状態と進捗から、中央への到達度（ポジションレシオ）を計算する。"""
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
    """ゲージ進行度に基づいて「最も中央に近い（手前にいる）」ターゲットを選定する。"""
    target_team = TeamType.ENEMY if my_team_type == TeamType.PLAYER else TeamType.PLAYER
    best_target = None
    max_ratio = float('-inf')
    
    candidates = world.get_entities_with_components('team', 'defeated', 'gauge')
    for teid, tcomps in candidates:
        if tcomps['team'].team_type == target_team and not tcomps['defeated'].is_defeated:
            ratio = calculate_gauge_ratio(tcomps['gauge'].status, tcomps['gauge'].progress)
            if ratio > max_ratio:
                max_ratio = ratio
                best_target = teid
    return best_target

def reset_gauge_to_cooldown(gauge):
    """行動終了後、クールダウン状態へ移行する。"""
    gauge.status = GaugeStatus.COOLDOWN
    gauge.progress = 0.0