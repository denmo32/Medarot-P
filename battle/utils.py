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
    InputSystem(プレイヤー)とAISystem(エネミー)の両方から呼ばれる
    """
    comps = world.entities[eid]
    gauge = comps['gauge']
    context = world.entities[0]['battlecontext'] # Singleton想定
    flow = world.entities[0]['battleflow']

    gauge.selected_action = action
    gauge.selected_part = part

    # 時間計算
    if action == ActionType.ATTACK and part:
        # パーツ情報の取得
        part_id = comps['partlist'].parts.get(part)
        p_comps = world.entities[part_id]
        
        # 基本時間計算
        # 属性ボーナス（Power）による攻撃力上昇が速度低下を招かないよう、base_attackを使用する
        atk = p_comps['attack'].base_attack
        c_t, cd_t = calculate_action_times(atk)
        gauge.charging_time = c_t
        gauge.cooldown_time = cd_t
        
        # 属性ボーナス（時間短縮）の適用
        # メダルとパーツの属性が一致し、かつ「スピード」属性の場合のみ適用
        medal_comp = comps.get('medal')
        part_comp = p_comps.get('part')
        
        if medal_comp and part_comp:
            if medal_comp.attribute == part_comp.attribute and medal_comp.attribute == "speed":
                gauge.charging_time *= 0.80
                gauge.cooldown_time *= 0.80
    
    # チャージ開始
    gauge.status = GaugeStatus.CHARGING
    gauge.progress = 0.0
    
    # フェーズ遷移 (IDLEに戻す)
    context.current_turn_entity_id = None
    flow.current_phase = BattlePhase.IDLE
    
    # 待機列から削除
    if context.waiting_queue and context.waiting_queue[0] == eid:
        context.waiting_queue.pop(0)

def calculate_current_x(base_x: int, status: str, progress: float, team_type: str) -> float:
    """エンティティの現在のアイコンX座標を計算する（ゲージ進行に基づく視覚的座標）"""
    center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
    offset = 40 # 実行地点のセンターからのオフセット
    
    if team_type == TeamType.PLAYER:
        # プレイヤー側：右（中央）に向かって進む
        # 待機位置: base_x, 実行位置: center_x - offset
        target_x = center_x - offset
        if status == GaugeStatus.CHARGING:
            return base_x + (progress / 100.0) * (target_x - base_x)
        if status == GaugeStatus.EXECUTING:
            return target_x
        if status == GaugeStatus.COOLDOWN:
            return target_x - (progress / 100.0) * (target_x - base_x)
        return base_x
    else:
        # エネミー側：左（中央）に向かって進む
        # 待機位置: base_x + gauge_width, 実行位置: center_x + offset
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
    """
    現在のゲージ位置に基づき、最も「中央（敵陣側）」に近い敵対エンティティのIDを返す。
    """
    target_team = TeamType.ENEMY if my_team_type == TeamType.PLAYER else TeamType.PLAYER
    best_target = None
    
    # プレイヤー視点：敵の中でX座標が最小（左側＝中央寄り）のものが一番近い
    # エネミー視点：プレイヤーの中でX座標が最大（右側＝中央寄り）のものが一番近い
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

def calculate_action_menu_layout(button_count: int = 4):
    """アクションメニューのボタン配置を計算し、各ボタンの矩形情報を返す"""
    wx, wy = 0, GAME_PARAMS['MESSAGE_WINDOW_Y']
    wh = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
    pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']
    ui_cfg = GAME_PARAMS['UI']

    btn_y = wy + wh - ui_cfg['BTN_Y_OFFSET']
    btn_w, btn_h, btn_pad = ui_cfg['BTN_WIDTH'], ui_cfg['BTN_HEIGHT'], ui_cfg['BTN_PADDING']
    
    layout = []
    for i in range(button_count):
        bx = wx + pad + i * (btn_w + btn_pad)
        layout.append({'x': bx, 'y': btn_y, 'w': btn_w, 'h': btn_h})
        
    return layout

def reset_gauge_to_cooldown(gauge):
    """ゲージをクールダウン開始状態（実行ライン地点）にリセットする"""
    gauge.status = GaugeStatus.COOLDOWN
    gauge.progress = 0.0
    gauge.selected_action = None
    gauge.selected_part = None

def interrupt_gauge_return_home(gauge):
    """
    アクションを中断し、現在地点からホームへ戻るクールダウンを開始する。
    チャージ進行度(0->100)を、同じ位置に対応するクールダウン進行度へ変換する。
    """
    current_p = gauge.progress
    gauge.status = GaugeStatus.COOLDOWN
    # チャージPとクールダウンQが同じ位置になる条件: Q = 100 - P
    gauge.progress = max(0.0, 100.0 - current_p)
    gauge.selected_action = None
    gauge.selected_part = None

def is_target_valid(world, target_id: Optional[int], target_part: Optional[str] = None) -> bool:
    """
    ターゲット機体および部位が生存しているか検証する共通関数
    
    Args:
        world: ECS World
        target_id: 対象エンティティID
        target_part: (Option) 対象パーツ名 (e.g., PartType.HEAD)
        
    Returns:
        bool: ターゲットが有効（生存）ならTrue
    """
    if target_id is None:
        return False
        
    t_comps = world.try_get_entity(target_id)
    if not t_comps:
        return False
    
    # 機体が敗北していないか
    if 'defeated' in t_comps and t_comps['defeated'].is_defeated:
        return False
        
    # 部位指定がある場合、その部位が破壊されていないか
    if target_part:
        if 'partlist' not in t_comps:
            return False
            
        p_id = t_comps['partlist'].parts.get(target_part)
        if not p_id:
            return False
            
        p_comps = world.try_get_entity(p_id)
        if not p_comps or 'health' not in p_comps:
            return False
            
        if p_comps['health'].hp <= 0:
            return False
            
    return True