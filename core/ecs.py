"""ECSエンジン（汎用的な基盤のみ）"""

from typing import Dict, Any, List, Optional

class Entity:
    """エンティティ：ゲーム内のオブジェクトを識別するID"""
    def __init__(self, entity_id: int):
        self.id = entity_id

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
        self.entities: Dict[int, Dict[str, Component]] = {}
        self.next_entity_id = 0

    def create_entity(self) -> Entity:
        """新しいエンティティを作成"""
        entity = Entity(self.next_entity_id)
        self.entities[entity.id] = {}
        self.next_entity_id += 1
        return entity

    def add_component(self, entity_id: int, component: Component, component_name: Optional[str] = None) -> None:
        """エンティティにコンポーネントを追加"""
        if entity_id not in self.entities:
            raise ValueError(f"Entity with id {entity_id} does not exist")

        # コンポーネント名が指定されていない場合はクラス名を使用
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
        """指定されたコンポーネントを持つすべてのエンティティを取得"""
        result = []
        for entity_id, components in self.entities.items():
            has_all_components = True
            for name in component_names:
                if name not in components:
                    has_all_components = False
                    break
            if has_all_components:
                result.append((entity_id, components))
        return result

