"""入力データ用コンポーネント"""

from dataclasses import dataclass, field
from typing import List, Tuple
from core.ecs import Component

@dataclass
class InputComponent(Component):
    """
    ユーザー入力の状態（論理入力）を保持するコンポーネント。
    
    座標情報は持たず、UI 層で判定済みの「論理コマンド」のみを保持する。
    これにより ECS ロジック層は画面座標の概念から完全に分離される。
    """
    # 論理ボタンフラグ（押下された瞬間のみ True）
    btn_ok: bool = False      # 決定 (Z, Enter, Click)
    btn_cancel: bool = False  # キャンセル (X, Backspace)
    btn_menu: bool = False    # メニュー/中断 (Esc)

    # 方向入力
    btn_left: bool = False
    btn_right: bool = False
    btn_up: bool = False
    btn_down: bool = False

    # UI からの論理コマンドキュー
    # 例：[("attack", "head"), ("skip", None)]
    action_commands: List[Tuple[str, str | None]] = field(default_factory=list)

    # 選択インデックス変更コマンド（キーボード/マウス選択用）
    # 直接 InputComponent.selected_menu_index を持たせることも可能だが、
    # 「変更コマンド」として明示的に扱うことで意図を明確にする
    selected_menu_index: int | None = None
