"""バトル系システムの基底クラス

ECS の World を直接操作することを基本とし、
頻繁にアクセスする Context と Flow へのショートカットのみを提供する。
"""

from typing import Optional, Dict, Any
from core.ecs import System
from battle.mechanics.flow import get_battle_state


class BattleSystemBase(System):
    """
    バトルシステム共通の基底クラス。
    """
    @property
    def context(self):
        ctx, _ = get_battle_state(self.world)
        return ctx

    @property
    def flow(self):
        _, flow = get_battle_state(self.world)
        return flow

    def is_ready(self, required_phase: Optional[str] = None) -> bool:
        """
        システムが更新処理を実行できる状態かチェックする。
        
        Args:
            required_phase: 必要なフェーズ（指定しない場合はフェーズチェックをスキップ）
        
        Returns:
            実行可能な場合は True
        """
        if not self.context or not self.flow:
            return False
        if required_phase and self.flow.current_phase != required_phase:
            return False
        return True

    def get_entity_name(self, entity_id: int) -> str:
        """
        エンティティの名前を取得する。
        
        Args:
            entity_id: エンティティID
        
        Returns:
            エンティティの名前（見つからない場合は "Unknown"）
        """
        comps = self.world.try_get_entity(entity_id)
        if comps and 'medal' in comps:
            return comps['medal'].nickname
        return "Unknown"

    def get_entity_comps(self, entity_id: int, *component_names: str) -> Optional[Dict[str, Any]]:
        """
        エンティティから指定されたコンポーネントを取得する。
        一つでも欠けていれば None を返す。
        
        Args:
            entity_id: エンティティID
            component_names: 取得するコンポーネント名
        
        Returns:
            コンポーネント辞書（見つからない場合は None）
        """
        return self.world.try_get_components(entity_id, *component_names)
