"""プレイヤーの保存データ（編成など）を管理するクラス"""

import json
import os
from typing import List, Dict
from data.game_data_manager import get_game_data_manager

class SaveDataManager:
    """プレイヤーのゲーム進行データ（現在は編成のみ）を保持"""
    
    def __init__(self):
        # データの保存先パスを設定
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.save_file_path = os.path.join(current_dir, 'data', 'save_data.json')
        
        # データをロード、またはデフォルトを作成
        self.player_team = self._load_data()

    def _load_data(self) -> List[Dict]:
        """保存データを読み込む、なければデフォルトを作成"""
        if os.path.exists(self.save_file_path):
            try:
                with open(self.save_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('player_team', self._get_default_team())
            except (json.JSONDecodeError, IOError):
                print("セーブデータの読み込みに失敗しました。デフォルト設定を使用します。")
                return self._get_default_team()
        else:
            default_team = self._get_default_team()
            self._save_data(default_team)
            return default_team

    def _save_data(self, team_data: List[Dict]):
        """データをファイルに保存"""
        data = {'player_team': team_data}
        try:
            with open(self.save_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError:
            print("セーブデータの保存に失敗しました。")

    def _get_default_team(self) -> List[Dict]:
        """デフォルトの3機編成を作成"""
        dm = get_game_data_manager()
        team = []
        
        # 3機分作成
        names = ["機体1", "機体2", "機体3"]
        
        # パーツIDリストを取得（空の場合は安全策としてダミーIDを使用）
        medal_ids = dm.get_part_ids_for_type("medal") or ["medal_001"]
        head_ids = dm.get_part_ids_for_type("head") or ["head_001"]
        r_arm_ids = dm.get_part_ids_for_type("right_arm") or ["rarm_001"]
        l_arm_ids = dm.get_part_ids_for_type("left_arm") or ["larm_001"]
        legs_ids = dm.get_part_ids_for_type("legs") or ["legs_001"]

        for i in range(3):
            setup = {
                "name": names[i] if i < len(names) else f"メダロット{i+1}",
                "medal": medal_ids[i % len(medal_ids)],
                "parts": {
                    "head": head_ids[i % len(head_ids)],
                    "right_arm": r_arm_ids[i % len(r_arm_ids)],
                    "left_arm": l_arm_ids[i % len(l_arm_ids)],
                    "legs": legs_ids[i % len(legs_ids)],
                }
            }
            team.append(setup)
        return team

    def update_part(self, machine_idx: int, part_type: str, part_id: str):
        """指定した機体のパーツ（またはメダル）を更新"""
        if 0 <= machine_idx < len(self.player_team):
            if part_type == "medal":
                self.player_team[machine_idx]["medal"] = part_id
            else:
                self.player_team[machine_idx]["parts"][part_type] = part_id
            
            # 更新時に即保存
            self._save_data(self.player_team)

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