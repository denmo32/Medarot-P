"""パーツデータ管理クラス"""

import json
import os
from typing import Dict, Any, List

class PartsDataManager:
    """parts_data.jsonからパーツデータを管理するクラス"""

    # 部位の表示名マッピング
    PART_TYPE_LABELS = {
        'head': '頭部',
        'right_arm': '右腕',
        'left_arm': '左腕',
        'legs': '脚部'
    }

    def __init__(self, json_path: str = None):
        """初期化
        
        Args:
            json_path: parts_data.jsonへのパス（Noneの場合はデフォルトパスを使用）
        """
        if json_path is None:
            # 現在のディレクトリ基準でparts_data.jsonのパスを決定
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.json_path = os.path.join(current_dir, 'data', 'parts_data.json')
        else:
            self.json_path = json_path
        
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """JSONファイルからデータを読み込む"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"警告: {self.json_path} が見つかりません")
            return {}
        except json.JSONDecodeError as e:
            print(f"警告: JSON解析エラー: {e}")
            return {}

    def get_part_data(self, part_id: str) -> Dict[str, Any]:
        """パーツIDからパーツデータを取得

        Args:
            part_id: パーツのID（例: 'head_001'）

        Returns:
            パーツのデータ辞書、存在しない場合は空辞書
        """
        parts = self.data.get('parts', {})
        for part_type, part_dict in parts.items():
            if part_id in part_dict:
                return part_dict[part_id]
        return {}

    def get_part_name(self, part_id: str) -> str:
        """パーツIDから表示名を取得

        Args:
            part_id: パーツのID

        Returns:
            パーツの表示名、存在しない場合はID本身
        """
        part_data = self.get_part_data(part_id)
        return part_data.get('name', part_id)

    def get_parts_for_part_type(self, part_type: str) -> Dict[str, Dict[str, Any]]:
        """部位タイプからその部位の全パーツを取得

        Args:
            part_type: 部位タイプ（'head', 'right_arm', 'left_arm', 'legs'）

        Returns:
            パーツIDをキーとしたパーツデータ辞書
        """
        parts = self.data.get('parts', {})
        return parts.get(part_type, {})

    def get_part_ids_for_type(self, part_type: str) -> List[str]:
        """部位タイプからパーツIDのリストを取得

        Args:
            part_type: 部位タイプ

        Returns:
            パーツIDのリスト
        """
        part_dict = self.get_parts_for_part_type(part_type)
        return list(part_dict.keys())

    def get_button_labels(self, is_player: bool = True) -> Dict[str, str]:
        """ボタン表示用のラベルを取得（部位タイプのラベル）

        Args:
            is_player: プレイヤーの場合はTrue、エネミーの場合はFalse（互換性のため）

        Returns:
            ボタン表示用のラベル辞書（部位タイプ -> ラベル）
        """
        return self.PART_TYPE_LABELS

    def reload_data(self) -> None:
        """データを再読み込み"""
        self.data = self._load_data()

# グローバルインスタンス（方便用）
_parts_manager = None

def get_parts_manager() -> PartsDataManager:
    """PartsDataManagerのグローバルインスタンスを取得"""
    global _parts_manager
    if _parts_manager is None:
        _parts_manager = PartsDataManager()
    return _parts_manager
