"""パーツ・メダルデータ管理クラス"""

import json
import logging
from typing import Dict, List, Optional, Union
from core.utils import resource_path
from domain.models import PartData, MedalData
from domain.constants import CustomizeSlot, PartType

logger = logging.getLogger(__name__)


class GameDataManager:
    """parts_data.jsonおよびmedals_data.jsonからデータを管理するクラス"""

    def __init__(self, parts_json_path: Optional[str] = None, medals_json_path: Optional[str] = None):
        self.parts_json_path = parts_json_path or resource_path('core/data/parts_data.json')
        self.medals_json_path = medals_json_path or resource_path('core/data/medals_data.json')

        raw_data = self._load_all_data()
        # 読み込み時点で部位を PartType に正規化して保持
        self._parts_by_type: Dict[PartType, Dict[str, dict]] = self._build_typed_parts(raw_data)
        # パース済みの不変オブジェクトを読み込み時に構築し、以降は同一インスタンスを再利用する
        # （PartData / MedalData は frozen なため、毎回 from_dict する意味はない）
        self._part_instances: Dict[str, PartData] = {
            pid: PartData.from_dict(raw)
            for parts in self._parts_by_type.values()
            for pid, raw in parts.items()
        }
        self._medal_instances: Dict[str, MedalData] = {
            mid: MedalData.from_dict(raw)
            for mid, raw in raw_data.get('medals', {}).items()
        }

    def _load_all_data(self) -> Dict:
        data = {}
        data.update(self._load_json(self.parts_json_path))
        data.update(self._load_json(self.medals_json_path))
        return data

    def _build_typed_parts(self, data: Dict) -> Dict[PartType, Dict[str, dict]]:
        typed_parts = {}
        for raw_pt, parts in data.get('parts', {}).items():
            pt = PartType.from_key(raw_pt)
            if pt:
                typed_parts[pt] = parts
            else:
                logger.warning(f"未知のパーツ部位キーを無視しました: {raw_pt}")
        return typed_parts

    def _load_json(self, path: str) -> Dict:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"データファイル読み込みエラー {path}: {e}")
            return {}

    def get_part_data(self, part_id: str) -> Optional[PartData]:
        return self._part_instances.get(part_id)

    def get_medal_data(self, medal_id: str) -> Optional[MedalData]:
        return self._medal_instances.get(medal_id)

    def get_part_name(self, item_id: str) -> str:
        if part_data := self.get_part_data(item_id):
            return part_data.name
        if medal_data := self.get_medal_data(item_id):
            return medal_data.name
        return item_id

    def get_part_ids_for_type(self, slot_type: Union[CustomizeSlot, PartType, str]) -> List[str]:
        """スロット（メダル / 各部位）から装着候補 ID 一覧を取得"""
        slot = CustomizeSlot.from_key(slot_type)
        if slot is None:
            return []
        if slot.is_medal:
            return list(self._medal_instances.keys())
        return list(self._parts_by_type.get(PartType(slot.value), {}).keys())