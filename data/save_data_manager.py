"""プレイヤーの保存データ（編成など）を管理するクラス"""

from typing import List, Dict
from data.parts_data_manager import get_parts_manager

class SaveDataManager:
    """プレイヤーのゲーム進行データ（現在は編成のみ）を保持"""
    
    def __init__(self):
        self.player_team = self._get_default_team()

    def _get_default_team(self) -> List[Dict]:
        """デフォルトの3機編成を作成"""
        pm = get_parts_manager()
        team = []
        
        # 3機分作成
        names = ["サイカチス", "ロクショウ", "ドークス"]
        for i in range(3):
            setup = {
                "name": names[i] if i < len(names) else f"メダロット{i+1}",
                "parts": {
                    "head": pm.get_part_ids_for_type("head")[i % 3],
                    "right_arm": pm.get_part_ids_for_type("right_arm")[i % 3],
                    "left_arm": pm.get_part_ids_for_type("left_arm")[i % 3],
                    "legs": pm.get_part_ids_for_type("legs")[i % 3],
                }
            }
            team.append(setup)
        return team

    def update_part(self, machine_idx: int, part_type: str, part_id: str):
        """指定した機体のパーツを更新"""
        if 0 <= machine_idx < len(self.player_team):
            self.player_team[machine_idx]["parts"][part_type] = part_id

    def get_machine_setup(self, machine_idx: int) -> Dict:
        """指定した機体のセットアップを取得"""
        if 0 <= machine_idx < len(self.player_team):
            return self.player_team[machine_idx]
        return {}

# グローバルインスタンス
_save_manager = None

def get_save_manager() -> SaveDataManager:
    global _save_manager
    if _save_manager is None:
        _save_manager = SaveDataManager()
    return _save_manager