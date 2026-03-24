"""バトル状態からのデータ取得専用クラス"""

from typing import Optional, Tuple, Dict, Any, List
from core.ecs import World
from battle.mechanics.flow import get_battle_state


class BattleQuery:
    """
    バトル状態からのデータ取得のみを行うクラス（副作用なし）。

    責任範囲:
    - エンティティ・コンポーネントの取得
    - 部位情報の取得
    - 生存状態の判定
    - チーム情報の取得
    - バトルコンテキスト・フローの参照
    """

    def __init__(self, world: World):
        self.world = world

    def try_get_components(self, entity_id: int, *names: str) -> Optional[Dict[str, Any]]:
        """指定エンティティから指定されたコンポーネントを安全に取得"""
        return self.world.try_get_components(entity_id, *names)

    def get_part_entity_id(self, entity_id: int, part_type: str) -> Optional[int]:
        """指定機体の指定部位のエンティティ ID を取得"""
        comps = self.try_get_components(entity_id, 'partlist')
        if not comps:
            return None
        return comps['partlist'].parts.get(part_type)

    def get_part_components(self, entity_id: int, part_type: str, *names: str) -> Optional[Dict[str, Any]]:
        """指定機体の指定部位から指定されたコンポーネントを取得"""
        pid = self.get_part_entity_id(entity_id, part_type)
        if pid is None:
            return None
        return self.try_get_components(pid, *names)

    def is_entity_alive(self, entity_id: int) -> bool:
        """エンティティが生存しているか（敗北フラグが立っていないか）"""
        comps = self.world.try_get_entity(entity_id)
        if not comps:
            return False
        defeated = comps.get('defeated')
        return not defeated.is_defeated if defeated else True

    def is_part_alive(self, entity_id: int, part_type: str) -> bool:
        """
        指定部位が生存しているか（HP > 0 かつ機体が機能停止していない）。
        
        Args:
            entity_id: 機体エンティティ ID
            part_type: 部位種別（PartType）
        
        Returns:
            機体が機能停止しておらず、かつ部位 HP が 1 以上なら True
        """
        # 機体全体の生存チェック（機能停止判定）
        entity_comps = self.world.try_get_entity(entity_id)
        if entity_comps:
            defeated = entity_comps.get('defeated')
            if defeated and defeated.is_defeated:
                return False  # 機能停止している場合は全て NG
        
        # 部位の HP チェック
        p_comps = self.get_part_components(entity_id, part_type, 'health')
        return p_comps and p_comps['health'].hp > 0

    def get_alive_parts_hp(self, entity_id: int) -> Dict[str, int]:
        """生存している部位名とその HP の辞書を取得"""
        comps = self.try_get_components(entity_id, 'partlist')
        if not comps:
            return {}

        result = {}
        for pt, pid in comps['partlist'].parts.items():
            p_comps = self.world.try_get_entity(pid)
            if p_comps and 'health' in p_comps:
                hp = p_comps['health'].hp
                if hp > 0:
                    result[pt] = hp
        return result

    def get_team_entities(self, team_type: str, only_alive: bool = True) -> List[int]:
        """指定チームのエンティティ ID リストを取得"""
        result = []
        for eid, comps in self.world.get_entities_with_components('team'):
            if comps['team'].team_type == team_type:
                if not only_alive or self.is_entity_alive(eid):
                    result.append(eid)
        return result

    def get_entities_with_components(self, *names: str) -> List[Tuple[int, Dict[str, Any]]]:
        """指定されたコンポーネントをすべて持つエンティティのリストを取得"""
        return self.world.get_entities_with_components(*names)

    @property
    def context(self) -> Optional[Dict[str, Any]]:
        """BattleContextComponent へのアクセス"""
        ctx, _ = get_battle_state(self.world)
        return ctx

    @property
    def flow(self) -> Optional[Dict[str, Any]]:
        """BattleFlowComponent へのアクセス"""
        _, flow = get_battle_state(self.world)
        return flow
