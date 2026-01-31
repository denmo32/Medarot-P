"""バトル固有のECSコンポーネント定義（純粋データ構造）"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from core.ecs import Component
from battle.constants import GaugeStatus

@dataclass
class StatusEffect:
    """汎用的な状態異常データ"""
    type_id: str             # "stop", "burn", "virus" 等
    duration: float          # 残り時間
    params: Dict[str, Any] = field(default_factory=dict) # 任意のパラメータ

@dataclass
class GaugeComponent(Component):
    """ATBゲージコンポーネント"""
    value: float = 0.0
    status: str = GaugeStatus.ACTION_CHOICE
    
    progress: float = field(init=False, default=0.0)
    selected_action: Optional[str] = field(init=False, default=None)
    selected_part: Optional[str] = field(init=False, default=None)
    part_targets: Dict[str, Optional[int]] = field(default_factory=dict)
    
    charging_time: float = field(init=False, default=2.0)
    cooldown_time: float = field(init=False, default=2.0)
    
    # 状態異常：汎用リストに変更
    active_effects: List[StatusEffect] = field(default_factory=list)

@dataclass
class TeamComponent(Component):
    """チーム属性"""
    team_type: str            # "player", "enemy"
    team_color: tuple
    is_leader: bool = False

@dataclass
class RenderComponent(Component):
    """描画サイズ情報"""
    width: int
    height: int
    gauge_width: int
    gauge_height: int

@dataclass
class PartComponent(Component):
    """パーツの種類と属性"""
    part_type: str            # "head", "right_arm", "left_arm", "legs"
    attribute: str = "undefined"

@dataclass
class HealthComponent(Component):
    """HPデータ"""
    hp: int
    max_hp: int
    display_hp: float = field(init=False)

    def __post_init__(self):
        self.display_hp = float(self.hp)

@dataclass
class AttackComponent(Component):
    """攻撃性能（脚部以外）"""
    attack: int                # 現在の攻撃力（ボーナス込み）
    trait: Optional[str] = None     # "ライフル", "ソード", "サンダー" 等
    success: int = 0           # 成功度
    base_attack: Optional[int] = None # 時間計算用の基本攻撃力
    time_modifier: float = 1.0 # 充填・放熱時間の補正係数（属性一致ボーナス等）
    skill_type: str = "shoot"  # "shoot", "strike", "aimed_shot", "reckless"

    def __post_init__(self):
        if self.base_attack is None:
            self.base_attack = self.attack

@dataclass
class MobilityComponent(Component):
    """機動・防御性能（脚部）"""
    mobility: int
    defense: int = 0

@dataclass
class PartListComponent(Component):
    """機体が構成するパーツエンティティIDの辞書"""
    parts: Dict[str, int] = field(default_factory=dict)

@dataclass
class MedalComponent(Component):
    """メダル（頭脳）データ"""
    medal_id: str
    medal_name: str
    nickname: str
    personality_id: str = "random"
    attribute: str = "undefined"

@dataclass
class DefeatedComponent(Component):
    """敗北フラグ"""
    is_defeated: bool = False

@dataclass
class BattleContextComponent(Component):
    """
    バトルログや待機列などの共有データ。
    """
    waiting_queue: List[int] = field(default_factory=list)
    current_turn_entity_id: Optional[int] = None
    battle_log: List[str] = field(default_factory=list)
    pending_logs: List[str] = field(default_factory=list) # ダメージ詳細などの一時バッファ
    selected_menu_index: int = 0

@dataclass
class DamageEventComponent(Component):
    """ダメージ発生を伝える一時的なコンポーネント"""
    attacker_id: int
    attacker_part: str
    damage: int
    target_part: str
    is_critical: bool = False
    # 追加効果のリスト
    added_effects: List[StatusEffect] = field(default_factory=list)