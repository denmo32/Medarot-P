"""バトル固有のECSコンポーネント定義"""

from typing import List, Optional, Dict
from core.ecs import Component

class PartHealthComponent(Component):
    """パーツごとのHPコンポーネント（統一版 - is_defeated削除）"""
    def __init__(self, head_hp: int, right_arm_hp: int, left_arm_hp: int, leg_hp: int,
                 max_head_hp: int, max_right_arm_hp: int, max_left_arm_hp: int, max_leg_hp: int):
        self.head_hp = head_hp
        self.right_arm_hp = right_arm_hp
        self.left_arm_hp = left_arm_hp
        self.leg_hp = leg_hp
        self.max_head_hp = max_head_hp
        self.max_right_arm_hp = max_right_arm_hp
        self.max_left_arm_hp = max_left_arm_hp
        self.max_leg_hp = max_leg_hp
        # is_defeatedはDefeatedComponentに移動し、統一管理

class GaugeComponent(Component):
    """ATBゲージコンポーネント（純粋データ）"""
    # 行動状態の定義
    ACTION_CHOICE = "action_choice"
    CHARGING = "charging"
    EXECUTING = "executing"
    COOLDOWN = "cooldown"

    def __init__(self, value: float = 0.0, speed: float = 0.1, status: str = None):
        self.value = value
        self.speed = speed
        self.status = status or self.ACTION_CHOICE
        self.progress = 0.0
        self.selected_action: Optional[str] = None  # "attack", "skip"
        self.selected_part: Optional[str] = None    # "head", "right_arm", "left_arm"
        self.action_choice_time = 3.0
        self.charging_time = 2.0
        self.executing_time = 1.0
        self.cooldown_time = 2.0

class TeamComponent(Component):
    """チームコンポーネント（純粋データ）"""
    def __init__(self, team_type: str, team_color: tuple):
        self.team_type = team_type # "player" or "enemy"
        self.team_color = team_color

class PartAttackComponent(Component):
    """パーツごとの攻撃力コンポーネント（純粋データ）"""
    def __init__(self, head_attack: int, right_arm_attack: int, left_arm_attack: int):
        self.head_attack = head_attack
        self.right_arm_attack = right_arm_attack
        self.left_arm_attack = left_arm_attack

class RenderComponent(Component):
    """描画用コンポーネント（純粋データ）"""
    def __init__(self, width: int, height: int, gauge_width: int, gauge_height: int):
        self.width = width
        self.height = height
        self.gauge_width = gauge_width
        self.gauge_height = gauge_height

class PartComponent(Component):
    """パーツコンポーネント（パーツの種類を指定）"""
    def __init__(self, part_type: str):
        self.part_type = part_type  # "head", "right_arm", "left_arm", "leg"

class HealthComponent(Component):
    """個別パーツのHPコンポーネント"""
    def __init__(self, hp: int, max_hp: int):
        self.hp = hp
        self.max_hp = max_hp

class AttackComponent(Component):
    """個別パーツの攻撃力コンポーネント（脚部以外）"""
    def __init__(self, attack: int):
        self.attack = attack

class PartListComponent(Component):
    """Medabotが持つパーツのリストコンポーネント"""
    def __init__(self):
        self.parts: Dict[str, int] = {}  # {"head": entity_id, "right_arm": entity_id, ...}

class DefeatedComponent(Component):
    """統一された敗北状態コンポーネント"""
    def __init__(self):
        self.is_defeated = False

class PartParametersComponent(Component):
    """パーツパラメータコンポーネント（将来の拡張用）"""
    def __init__(self, base_stats: dict, custom_mods: dict = None):
        self.base_stats = base_stats  # 基本パラメータ
        self.custom_mods = custom_mods or {}  # カスタマイズMOD
        self.is_customized = bool(custom_mods)

class BattleContextComponent(Component):
    """
    バトル全体のグローバルな状態を保持するコンポーネント。
    """
    def __init__(self):
        # バトル進行管理
        self.waiting_queue: List[int] = []
        self.current_turn_entity_id: Optional[int] = None

        # UI状態管理
        self.battle_log: List[str] = []
        self.waiting_for_input: bool = False       # メッセージ送り待ち
        self.waiting_for_action: bool = False      # 行動選択待ち
        self.game_over: bool = False
        self.winner: Optional[str] = None
