"""バトル固有のECSコンポーネント定義（純粋データ構造）"""

from typing import List, Optional, Dict
from core.ecs import Component

class GaugeComponent(Component):
    """ATBゲージコンポーネント"""
    ACTION_CHOICE = "action_choice"
    CHARGING = "charging"
    EXECUTING = "executing"
    COOLDOWN = "cooldown"

    def __init__(self, value: float = 0.0, speed: float = 0.1, status: str = None):
        self.value = value
        self.speed = speed
        self.status = status or self.ACTION_CHOICE
        self.progress = 0.0
        self.selected_action: Optional[str] = None
        self.selected_part: Optional[str] = None
        self.part_targets: Dict[str, Optional[int]] = {}
        
        self.charging_time = 2.0
        self.cooldown_time = 2.0
        
        # 状態異常：停止用タイマー（秒）
        self.stop_timer = 0.0

class TeamComponent(Component):
    """チーム属性"""
    def __init__(self, team_type: str, team_color: tuple, is_leader: bool = False):
        self.team_type = team_type # "player", "enemy"
        self.team_color = team_color
        self.is_leader = is_leader

class RenderComponent(Component):
    """描画サイズ情報"""
    def __init__(self, width: int, height: int, gauge_width: int, gauge_height: int):
        self.width = width
        self.height = height
        self.gauge_width = gauge_width
        self.gauge_height = gauge_height

class PartComponent(Component):
    """パーツの種類"""
    def __init__(self, part_type: str):
        self.part_type = part_type # "head", "right_arm", "left_arm", "legs"

class HealthComponent(Component):
    """HPデータ"""
    def __init__(self, hp: int, max_hp: int):
        self.hp = hp
        self.max_hp = max_hp

class AttackComponent(Component):
    """攻撃性能（脚部以外）"""
    def __init__(self, attack: int, trait: str = None, success: int = 0):
        self.attack = attack
        self.trait = trait # "ライフル", "ソード", "サンダー" 等
        self.success = success # 成功度

class MobilityComponent(Component):
    """機動・防御性能（脚部）"""
    def __init__(self, mobility: int, defense: int = 0):
        self.mobility = mobility
        self.defense = defense

class PartListComponent(Component):
    """機体が構成するパーツエンティティIDの辞書"""
    def __init__(self):
        self.parts: Dict[str, int] = {} 

class MedalComponent(Component):
    """メダル（頭脳）データ"""
    def __init__(self, medal_id: str, medal_name: str, nickname: str, personality_id: str = "random"):
        self.medal_id = medal_id
        self.medal_name = medal_name
        self.nickname = nickname
        self.personality_id = personality_id

class DefeatedComponent(Component):
    """敗北フラグ"""
    def __init__(self):
        self.is_defeated = False

class BattleContextComponent(Component):
    """
    バトルログや待機列などの共有データ。
    ※ 状態管理フラグは BattleFlowComponent に移動しました。
    """
    def __init__(self):
        self.waiting_queue: List[int] = []
        self.current_turn_entity_id: Optional[int] = None
        self.battle_log: List[str] = []
        self.pending_logs: List[str] = [] # ダメージ詳細などの一時バッファ
        self.selected_menu_index: int = 0

class DamageEventComponent(Component):
    """ダメージ発生を伝える一時的なコンポーネント"""
    def __init__(self, attacker_id: int, attacker_part: str, damage: int, target_part: str, is_critical: bool = False, stop_duration: float = 0.0):
        self.attacker_id = attacker_id
        self.attacker_part = attacker_part
        self.damage = damage
        self.target_part = target_part
        self.is_critical = is_critical
        self.stop_duration = stop_duration # 停止させる時間