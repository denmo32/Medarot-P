"""
バトル描画に必要な全データ構造（スナップショット）定義。
ロジック層のコンポーネントには一切依存しない、純粋なデータクラス（DTO）。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any

@dataclass
class CharacterViewData:
    """フィールド上のキャラクター1体の描画データ"""
    entity_id: int
    x: int
    y: int
    icon_x: float
    home_x: int
    home_y: int
    team_color: Tuple[int, int, int]
    name: str
    border_color: Optional[Tuple[int, int, int]]
    part_status: Dict[str, bool] # 部位生存フラグ

@dataclass
class ActionButtonData:
    """コマンドボタン情報"""
    label: str
    enabled: bool

@dataclass
class LogWindowData:
    """ログウィンドウ情報"""
    logs: List[str] = field(default_factory=list)
    show_input_guidance: bool = False
    is_active: bool = False

@dataclass
class ActionMenuData:
    """アクション選択メニュー情報"""
    actor_name: str = ""
    buttons: List[ActionButtonData] = field(default_factory=list)
    selected_index: int = 0
    is_active: bool = False

@dataclass
class GameOverData:
    """ゲームオーバー画面情報"""
    winner: str = ""
    is_active: bool = False

@dataclass
class CutinStateData:
    """カットイン演出の全情報"""
    is_active: bool = False
    bg_alpha: int = 0
    bar_height: int = 0
    mirror: bool = False
    
    # キャラクター表示
    attacker: Dict[str, Any] = field(default_factory=dict)
    defender: Dict[str, Any] = field(default_factory=dict)
    
    # オブジェクト
    bullet: Dict[str, Any] = field(default_factory=dict)
    effect: Dict[str, Any] = field(default_factory=dict)
    popup: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BattleStateSnapshot:
    """1フレームの描画に必要なバトルの全状態"""
    
    # フィールド情報
    characters: Dict[int, CharacterViewData] = field(default_factory=dict)
    
    # ターゲット指示ライン
    target_line: Optional[Tuple[CharacterViewData, CharacterViewData, float]] = None
    
    # ターゲットマーカー（メニュー選択中の予定ターゲット）
    target_marker_eid: Optional[int] = None

    # UIパネル
    log_window: LogWindowData = field(default_factory=LogWindowData)
    action_menu: ActionMenuData = field(default_factory=ActionMenuData)
    game_over: GameOverData = field(default_factory=GameOverData)
    
    # 演出
    cutin: CutinStateData = field(default_factory=CutinStateData)