"""パーツ・メダルデータ管理クラス"""

import json
import os
from typing import Dict, Any, List

class GameDataManager:
    """parts_data.jsonおよびmedals_data.jsonからデータを管理するクラス"""

    # 部位・項目の表示名マッピング
    PART_TYPE_LABELS = {
        'medal': 'メダル',
        'head': '頭部',
        'right_arm': '右腕',
        'left_arm': '左腕',
        'legs': '脚部'
    }

    # 属性の表示名マッピング
    ATTRIBUTE_LABELS = {
        'speed': 'スピード',
        'power': 'パワー',
        'technique': 'テクニック',
        'undefined': 'ー'
    }

    def __init__(self, json_path: str = None):
        """初期化"""
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # デフォルトのファイルパス
        self.parts_json_path = os.path.join(current_dir, 'data', 'parts_data.json')
        self.medals_json_path = os.path.join(current_dir, 'data', 'medals_data.json')

        # 引数でパスが指定された場合は、それをパーツデータパスとして優先使用（テスト容易性のため）
        if json_path is not None:
            self.parts_json_path = json_path
        
        self.data = self._load_all_data()
    
    def _load_all_data(self) -> Dict[str, Any]:
        """全データを読み込んで統合する"""
        data = {}
        
        # パーツデータ読み込み
        parts_data = self._load_json(self.parts_json_path)
        data.update(parts_data)
        
        # メダルデータ読み込み
        medals_data = self._load_json(self.medals_json_path)
        data.update(medals_data)
        
        return data

    def _load_json(self, path: str) -> Dict[str, Any]:
        """単一のJSONファイルを読み込む"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"警告: {path} が見つかりません")
            return {}
        except json.JSONDecodeError as e:
            print(f"警告: JSON解析エラー {path}: {e}")
            return {}

    def get_part_data(self, part_id: str) -> Dict[str, Any]:
        """パーツIDからパーツデータを取得"""
        parts = self.data.get('parts', {})
        for part_type, part_dict in parts.items():
            if part_id in part_dict:
                return part_dict[part_id]
        return {}

    def get_medal_data(self, medal_id: str) -> Dict[str, Any]:
        """メダルIDからメダルデータを取得"""
        return self.data.get('medals', {}).get(medal_id, {})

    def get_part_name(self, item_id: str) -> str:
        """IDから表示名（パーツ名またはメダル名）を取得"""
        # パーツから探す
        data = self.get_part_data(item_id)
        if not data:
            # メダルから探す
            data = self.get_medal_data(item_id)
            
        return data.get('name', item_id)

    def get_parts_for_part_type(self, part_type: str) -> Dict[str, Dict[str, Any]]:
        """部位タイプからその部位の全パーツを取得"""
        parts = self.data.get('parts', {})
        return parts.get(part_type, {})

    def get_part_ids_for_type(self, part_type: str) -> List[str]:
        """部位タイプまたはメダルからIDのリストを取得"""
        if part_type == "medal":
            return list(self.data.get('medals', {}).keys())
        
        part_dict = self.get_parts_for_part_type(part_type)
        return list(part_dict.keys())

    def get_button_labels(self, is_player: bool = True) -> Dict[str, str]:
        """ボタン表示用のラベルを取得"""
        return self.PART_TYPE_LABELS

    def get_attribute_label(self, attr_key: str) -> str:
        """属性キーから表示名を取得"""
        return self.ATTRIBUTE_LABELS.get(attr_key, attr_key)

    def get_next_part_id(self, current_id: str, direction: int = 1) -> str:
        """現在選択中のアイテムの次または前のIDを取得"""
        # まず部位を探す
        target_type = None
        parts = self.data.get('parts', {})
        for p_type, p_dict in parts.items():
            if current_id in p_dict:
                target_type = p_type
                break
        
        # パーツに見つからなければメダル
        if not target_type:
            if current_id in self.data.get('medals', {}):
                target_type = "medal"

        if not target_type: return current_id
        
        ids = self.get_part_ids_for_type(target_type)
        idx = ids.index(current_id)
        new_idx = (idx + direction) % len(ids)
        return ids[new_idx]

    def reload_data(self) -> None:
        """データを再読み込み"""
        self.data = self._load_all_data()

# グローバルインスタンス
_game_data_manager = None

def get_game_data_manager() -> GameDataManager:
    """GameDataManagerのグローバルインスタンスを取得"""
    global _game_data_manager
    if _game_data_manager is None:
        _game_data_manager = GameDataManager()
    return _game_data_manager