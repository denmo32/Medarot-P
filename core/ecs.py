"""ECSエンジン（汎用的な基盤のみ）"""

from typing import Dict, Any, List, Optional

class Component:
    """コンポーネント：データのみを持つ基底クラス"""
    pass

class System:
    """システム：コンポーネントを持つエンティティに対する処理を定義"""
    def __init__(self, world):
        self.world = world

    def update(self, dt: float):
        """システムの更新処理を実行"""
        pass

class World:
    """ECSのワールド：エンティティとコンポーネントの管理を行う"""
    def __init__(self):
        # Dict[entity_id, Dict[component_name, Component]]
        self.entities: Dict[int, Dict[str, Component]] = {}
        self.next_entity_id = 0

    def create_entity(self) -> int:
        """新しいエンティティ（ID）を作成"""
        eid = self.next_entity_id
        self.entities[eid] = {}
        self.next_entity_id += 1
        return eid

    def add_component(self, entity_id: int, component: Component, component_name: Optional[str] = None) -> None:
        """エンティティにコンポーネントを追加"""
        if entity_id not in self.entities:
            raise ValueError(f"Entity with id {entity_id} does not exist")

        if component_name is None:
            component_name = component.__class__.__name__.lower().replace('component', '')

        self.entities[entity_id][component_name] = component

    def remove_component(self, entity_id: int, component_name: str) -> None:
        """エンティティからコンポーネントを削除"""
        if entity_id in self.entities and component_name in self.entities[entity_id]:
            del self.entities[entity_id][component_name]

    def get_component(self, entity_id: int, component_name: str) -> Optional[Component]:
        """エンティティからコンポーネントを取得"""
        if entity_id in self.entities and component_name in self.entities[entity_id]:
            return self.entities[entity_id][component_name]
        return None

    def delete_entity(self, entity_id: int) -> None:
        """エンティティを削除"""
        if entity_id in self.entities:
            del self.entities[entity_id]

    def get_entities_with_components(self, *component_names: str) -> List[tuple]:
        """指定されたコンポーネントをすべて持つエンティティIDとそのコンポーネントDictのリストを取得"""
        result = []
        for entity_id, components in self.entities.items():
            if all(name in components for name in component_names):
                result.append((entity_id, components))
        return result