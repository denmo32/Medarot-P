"""ターゲット選定システム"""

from typing import Dict, Tuple, Optional
from battle.systems.base.battle_system_base import BattleSystemBase
from domain.ai_logic import get_personality
from domain.constants import GaugeStatus, PartType, TraitType
from battle.constants import BattlePhase


class TargetSelectionSystem(BattleSystemBase):
    """性格に基づき、各パーツの攻撃対象を事前に決定する"""

    def update(self, dt: float):
        flow = self.flow
        if not flow or flow.current_phase != BattlePhase.IDLE:
            return

        # 行動選択待ち（ACTION_CHOICE）状態かつ、まだターゲットが決まっていないエンティティを処理
        for eid, comps in self.world.get_entities_with_components('gauge', 'medal', 'defeated'):
            if comps['defeated'].is_defeated:
                continue

            gauge = comps['gauge']
            if gauge.status == GaugeStatus.ACTION_CHOICE and not gauge.part_targets:
                # System 側で必要なデータを抽出して純粋関数に渡す
                personality = get_personality(comps['medal'].personality_id)

                # 1. 生存している敵 ID リスト
                valid_enemy_ids = self._get_valid_enemy_ids(eid)

                # 2. 各パーツの射撃特性フラグ
                has_shooting_trait = self._get_shooting_trait_flags(eid)

                # 3. 敵の生存パーツ HP 情報
                enemy_parts = self._get_enemy_parts(valid_enemy_ids)

                # 純粋関数にデータを渡してターゲット選択
                targets = personality.select_targets(
                    valid_enemy_ids=valid_enemy_ids,
                    has_shooting_trait=has_shooting_trait,
                    enemy_parts=enemy_parts
                )
                gauge.part_targets = targets

    def _get_valid_enemy_ids(self, my_entity_id: int) -> list:
        """生存している敵機体の ID リストを取得"""
        my_comps = self.world.try_get_entity(my_entity_id)
        if not my_comps or 'team' not in my_comps:
            return []

        my_team = my_comps['team'].team_type
        target_team_type = "enemy" if my_team == "player" else "player"

        valid_ids = []
        for eid, ecomps in self.world.get_entities_with_components('team', 'defeated'):
            if ecomps['team'].team_type == target_team_type and not ecomps['defeated'].is_defeated:
                valid_ids.append(eid)

        return valid_ids

    def _get_shooting_trait_flags(self, entity_id: int) -> Dict[str, bool]:
        """各パーツの射撃特性フラグを取得"""
        flags = {}
        for part_type in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]:
            flags[part_type] = False
            entity_comps = self.world.try_get_entity(entity_id)
            if entity_comps and 'partlist' in entity_comps:
                part_id = entity_comps['partlist'].parts.get(part_type)
                if part_id:
                    p_comps = self.world.try_get_entity(part_id)
                    if p_comps and 'attack' in p_comps:
                        if p_comps['attack'].trait in TraitType.SHOOTING_TRAITS:
                            flags[part_type] = True
        return flags

    def _get_enemy_parts(self, enemy_ids: list) -> Dict[int, Dict[str, int]]:
        """敵の生存パーツ HP 情報を取得"""
        result = {}
        for eid in enemy_ids:
            result[eid] = self._get_alive_parts_hp(eid)
        return result

    def _get_alive_parts_hp(self, eid: int) -> Dict[str, int]:
        comps = self.world.try_get_entity(eid)
        if not comps or 'partlist' not in comps: return {}
        res = {}
        for pt, pid in comps['partlist'].parts.items():
            p_comps = self.world.try_get_entity(pid)
            if p_comps and 'health' in p_comps:
                hp = p_comps['health'].hp
                if hp > 0: res[pt] = hp
        return res

