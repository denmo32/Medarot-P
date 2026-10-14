"""プレイヤーの保存データ（編成など）を管理するクラス（アトミック保存・検証）"""

import json
import logging
import os
import tempfile
from typing import List, Dict, Optional
from domain.config import PLAYER_COUNT
from domain.constants import ALL_PART_TYPES, CustomizeSlot, PartType
from domain.models import RobotSetup, GameDataProtocol
from infra.paths import get_user_data_path

logger = logging.getLogger(__name__)


class SaveDataManager:
    """プレイヤーのゲーム進行データを管理（アトミック書き込み・欠損自動補完）"""

    def __init__(self, data_manager: GameDataProtocol):
        self.data_manager = data_manager
        self.save_file_path = get_user_data_path("save_data.json")
        self.player_team: List[RobotSetup] = self._load_and_validate_data()

    def _load_and_validate_data(self) -> List[RobotSetup]:
        """保存データを読み込み検証。ファイルがない・破損・不正時はフォールバック"""
        raw_list: List[dict] = []
        if os.path.exists(self.save_file_path):
            try:
                with open(self.save_file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    raw_list = content.get('player_team', [])
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"セーブデータの読み込み失敗 ({e})。デフォルトを作成します。")

        validated = [self._validate_or_fallback_setup(i, raw_list[i] if i < len(raw_list) else {})
                     for i in range(PLAYER_COUNT)]

        # 初回または修正が入った場合は最新の整形状態を保存
        self._save_data(validated)
        return validated

    def _validate_or_fallback_setup(self, idx: int, raw: dict) -> RobotSetup:
        name = raw.get("name") or f"機体{idx + 1}"

        # メダルの検証
        medal_id = raw.get("medal", "")
        if not self.data_manager.get_medal_data(medal_id):
            avail_medals = self.data_manager.get_part_ids_for_type(CustomizeSlot.MEDAL)
            medal_id = avail_medals[idx % len(avail_medals)] if avail_medals else "medal_001"

        # 各部位の検証（存在しないIDはデフォルトへ置換）
        raw_parts = raw.get("parts", {})
        part_ids: Dict[PartType, str] = {}
        for pt in ALL_PART_TYPES:
            pid = raw_parts.get(pt.value, "")
            if not self.data_manager.get_part_data(pid):
                defaults = self.data_manager.get_part_ids_for_type(pt)
                pid = defaults[idx % len(defaults)] if defaults else f"{pt.value}_001"
            part_ids[pt] = pid

        return RobotSetup(name=name, medal_id=medal_id, part_ids=part_ids)

    def _save_data(self, team_data: List[RobotSetup]):
        """アトミック書き込み: 一時ファイルに書いてから os.replace"""
        dir_name = os.path.dirname(self.save_file_path)
        os.makedirs(dir_name, exist_ok=True)

        payload = {'player_team': [s.to_dict() for s in team_data]}
        try:
            with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
                json.dump(payload, tf, ensure_ascii=False, indent=2)
                temp_path = tf.name
            os.replace(temp_path, self.save_file_path)
        except IOError as e:
            logger.error(f"セーブデータのアトミック保存に失敗しました: {e}")

    def update_part(self, robot_idx: int, slot_type: CustomizeSlot, part_id: str):
        """指定した機体のパーツ（またはメダル）を更新して保存"""
        if not (0 <= robot_idx < len(self.player_team)):
            return
        slot = CustomizeSlot.from_key(slot_type)
        if slot is None:
            return

        current = self.player_team[robot_idx]
        new_name = current.name
        new_medal = part_id if slot.is_medal else current.medal_id
        new_parts = dict(current.part_ids)
        if slot.part_type:
            new_parts[slot.part_type] = part_id

        self.player_team[robot_idx] = RobotSetup(name=new_name, medal_id=new_medal, part_ids=new_parts)
        self._save_data(self.player_team)

    def get_robot_setup(self, robot_idx: int) -> Optional[RobotSetup]:
        if 0 <= robot_idx < len(self.player_team):
            return self.player_team[robot_idx]
        return None

    def get_part_id(self, robot_idx: int, slot_type: CustomizeSlot) -> str:
        setup = self.get_robot_setup(robot_idx)
        slot = CustomizeSlot.from_key(slot_type)
        if not setup or slot is None:
            return ""
        return setup.get_part_id(slot)