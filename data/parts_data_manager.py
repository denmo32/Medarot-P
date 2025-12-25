"""パーツデータ管理クラス"""

import json
import os
from typing import Dict, Any

class PartsDataManager:
    """parts_data.jsonからパーツデータを管理するクラス"""
    
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
    
    def get_player_part_name(self, part_key: str) -> str:
        """プレイヤーパーツの表示名を取得
        
        Args:
            part_key: パーツのキー（'head', 'right_arm', 'left_arm', 'leg'）
            
        Returns:
            パーツの表示名（例: 'ヘッド', 'ライトアーム'）
        """
        player_parts = self.data.get('player_parts', {})
        part_data = player_parts.get(part_key, {})
        return part_data.get('name', part_key)  # デフォルトはキー本身
    
    def get_enemy_part_name(self, part_key: str) -> str:
        """エネミーパーツの表示名を取得
        
        Args:
            part_key: パーツのキー（'head', 'right_arm', 'left_arm', 'leg'）
            
        Returns:
            パーツの表示名（例: '敵ヘッド', '敵ライト阿姨'）
        """
        enemy_parts = self.data.get('enemy_parts', {})
        part_data = enemy_parts.get(part_key, {})
        return part_data.get('name', part_key)  # デフォルトはキー本身
    
    def get_all_player_part_names(self) -> Dict[str, str]:
        """プレイヤーパーツの全表示名を取得
        
        Returns:
             клюекры-part_key、value-表示名の辞書
        """
        player_parts = self.data.get('player_parts', {})
        return {key: part_data.get('name', key) for key, part_data in player_parts.items()}
    
    def get_all_enemy_part_names(self) -> Dict[str, str]:
        """エネミーパーツの全表示名を取得
        
        Returns:
             клюекры-part_key、value-表示名の辞書
        """
        enemy_parts = self.data.get('enemy_parts', {})
        return {key: part_data.get('name', key) for key, part_data in enemy_parts.items()}
    
    def get_button_labels(self, is_player: bool = True) -> Dict[str, str]:
        """ボタン表示用のラベルを取得
        
        Args:
            is_player: プレイヤーの場合はTrue、エネミーの場合はFalse
            
        Returns:
            ボタン表示用のラベル辞書
        """
        if is_player:
            return self.get_all_player_part_names()
        else:
            return self.get_all_enemy_part_names()
    
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
