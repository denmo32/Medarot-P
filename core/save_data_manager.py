"""プレイヤーの保存データ（編成・メダル熟練度など）を管理するクラス（アトミック保存・検証）"""

import json
import logging
import os
import tempfile
from typing import List, Dict, Optional, Sequence, Tuple
from domain.config import PLAYER_COUNT, MAX_MASTERY_VALUE
from domain.constants import ALL_PART_TYPES, ActionCategory, CustomizeSlot, PartType
from domain.models import CategoryProgress, RobotSetup, GameDataProtocol
from domain.proficiency import gain_mastery_exp
from core.paths import get_user_data_path

logger = logging.getLogger(__name__)


class SaveDataManager:
    """プレイヤーのゲーム進行データを管理（アトミック書き込み・欠損自動補完）"""

    def __init__(self, data_manager: GameDataProtocol):
        self.data_manager = data_manager
        self.save_file_path = get_user_data_path("save_data.json")
        self.player_team: List[RobotSetup] = []
        self.medals_progress: Dict[str, Dict[ActionCategory, CategoryProgress]] = {}
        self._load_and_validate_data()

    def _load_and_validate_data(self):
        """保存データを読み込み検証。ファイルがない・破損・不正時はフォールバック"""
        raw_team_list: List[dict] = []
        raw_medals_progress: dict = {}
        file_existed = os.path.exists(self.save_file_path)

        if file_existed:
            try:
                with open(self.save_file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    raw_team_list = content.get('player_team', [])
                    raw_medals_progress = content.get('medals_progress', {})
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"セーブデータの読み込み失敗 ({e})。デフォルトを作成します。")

        self.player_team = [
            self._validate_or_fallback_setup(i, raw_team_list[i] if i < len(raw_team_list) else {})
            for i in range(PLAYER_COUNT)
        ]

        self.medals_progress = self._validate_medals_progress(raw_medals_progress)

        current_dict_list = [s.to_dict() for s in self.player_team]
        current_medals_dict = {
            m_id: {cat.value: {"value": p.value, "exp": p.exp} for cat, p in cat_map.items()}
            for m_id, cat_map in self.medals_progress.items()
        }

        # 既存の内容と差分がある場合、または初回作成時のみ書き込む（メダル進捗の欠損時も確実に保存）
        if (not file_existed
                or raw_team_list != current_dict_list
                or raw_medals_progress != current_medals_dict):
            self._save_all()

    def _validate_medals_progress(self, raw_data: dict) -> Dict[str, Dict[ActionCategory, CategoryProgress]]:
        available_medals = self.data_manager.get_part_ids_for_type(CustomizeSlot.MEDAL)
        result: Dict[str, Dict[ActionCategory, CategoryProgress]] = {}

        for m_id in available_medals:
            m_raw = raw_data.get(m_id, {})
            cat_progress = {}
            for cat in ActionCategory:
                cat_raw = m_raw.get(cat.value, {})
                val = max(0, min(MAX_MASTERY_VALUE, int(cat_raw.get("value", 0))))
                exp = max(0, int(cat_raw.get("exp", 0)))
                # 余剰EXPの繰り上げおよびカンスト時のEXPゼロ正規化
                val, exp, _ = gain_mastery_exp(val, exp, gain=0)
                cat_progress[cat] = CategoryProgress(value=val, exp=exp)
            result[m_id] = cat_progress

        return result

    def _validate_or_fallback_setup(self, idx: int, raw: dict) -> RobotSetup:
        name = raw.get("name") or f"機体{idx + 1}"
        medal_id = raw.get("medal", "")
        if not self.data_manager.get_medal_data(medal_id):
            avail_medals = self.data_manager.get_part_ids_for_type(CustomizeSlot.MEDAL)
            medal_id = avail_medals[idx % len(avail_medals)] if avail_medals else "medal_001"

        raw_parts = raw.get("parts", {})
        part_ids: Dict[PartType, str] = {}
        for pt in ALL_PART_TYPES:
            pid = raw_parts.get(pt.value, "")
            if not self.data_manager.get_part_data(pid):
                defaults = self.data_manager.get_part_ids_for_type(pt)
                pid = defaults[idx % len(defaults)] if defaults else f"{pt.value}_001"
            part_ids[pt] = pid

        return RobotSetup(name=name, medal_id=medal_id, part_ids=part_ids)

    def _save_all(self):
        """アトミック書き込み: 一時ファイルに書いてから os.replace"""
        dir_name = os.path.dirname(self.save_file_path)
        os.makedirs(dir_name, exist_ok=True)

        payload = {
            'player_team': [s.to_dict() for s in self.player_team],
            'medals_progress': {
                m_id: {cat.value: {"value": prog.value, "exp": prog.exp} for cat, prog in cat_map.items()}
                for m_id, cat_map in self.medals_progress.items()
            }
        }
        try:
            with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
                json.dump(payload, tf, ensure_ascii=False, indent=2)
                temp_path = tf.name
            os.replace(temp_path, self.save_file_path)
        except IOError as e:
            logger.error(f"セーブデータのアトミック保存に失敗しました: {e}")

    def update_part(self, robot_idx: int, slot_type: CustomizeSlot, part_id: str):
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
        self._save_all()

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

    # === 熟練度関連 API ===

    def get_medal_mastery(self, medal_id: str, category: ActionCategory) -> int:
        cat_map = self.medals_progress.get(medal_id)
        if cat_map and category in cat_map:
            return cat_map[category].value
        return 0

    def get_medal_progress(self, medal_id: str, category: ActionCategory) -> CategoryProgress:
        cat_map = self.medals_progress.get(medal_id)
        if cat_map and category in cat_map:
            return cat_map[category]
        return CategoryProgress()

    def batch_add_medal_exp(self, updates: Sequence[Tuple[str, ActionCategory, int]]) -> None:
        """バトル終了時などに複数のEXP獲得を一括適用して保存する"""
        if not updates:
            return

        changed = False
        for medal_id, category, exp_gain in updates:
            if medal_id not in self.medals_progress:
                self.medals_progress[medal_id] = {cat: CategoryProgress() for cat in ActionCategory}

            current = self.medals_progress[medal_id].get(category, CategoryProgress())
            new_val, new_exp, _ = gain_mastery_exp(current.value, current.exp, gain=exp_gain)
            if new_val != current.value or new_exp != current.exp:
                self.medals_progress[medal_id][category] = CategoryProgress(value=new_val, exp=new_exp)
                changed = True

        if changed:
            self._save_all()