"""描画用データ（ViewModel）の生成ロジック"""

from typing import Dict, Any, List, Optional
from config import COLORS, GAME_PARAMS
from battle.constants import PartType, GaugeStatus, PART_LABELS, TeamType, BattlePhase
from battle.utils import calculate_current_x

class BattleViewModel:
    """RenderSystemが使用する描画データの生成・加工を担当"""

    HP_BAR_ORDER = [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]

    @staticmethod
    def get_character_view_data(world, eid: int, context, flow) -> Dict[str, Any]:
        """キャラクター（機体）の描画用データを収集"""
        comps = world.entities[eid]
        pos = comps['position']
        gauge = comps['gauge']
        team = comps['team']
        medal = comps['medal']
        part_list = comps['partlist']

        icon_x = calculate_current_x(pos.x, gauge.status, gauge.progress, team.team_type)
        border_color = BattleViewModel._get_border_color(eid, gauge, flow, context)
        part_status = BattleViewModel._get_part_status_map(world, part_list)
        home_x = pos.x + (GAME_PARAMS['GAUGE_WIDTH'] if team.team_type == TeamType.ENEMY else 0)

        return {
            'x': pos.x,
            'y': pos.y,
            'icon_x': icon_x,
            'home_x': home_x,
            'home_y': pos.y,
            'team_color': team.team_color,
            'name': medal.nickname,
            'border_color': border_color,
            'part_status': part_status
        }

    @staticmethod
    def _get_border_color(eid, gauge, flow, context):
        if eid == flow.active_actor_id or eid in context.waiting_queue or gauge.status == GaugeStatus.ACTION_CHOICE:
            return COLORS.get('BORDER_WAIT')
        if gauge.status == GaugeStatus.CHARGING:
            return COLORS.get('BORDER_CHARGE')
        if gauge.status == GaugeStatus.COOLDOWN:
            return COLORS.get('BORDER_COOLDOWN')
        return None

    @staticmethod
    def _get_part_status_map(world, part_list_comp) -> Dict[str, bool]:
        status = {}
        for p_type in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]:
            p_id = part_list_comp.parts.get(p_type)
            is_alive = False
            if p_id:
                hp = world.entities[p_id]['health'].hp
                if hp > 0:
                    is_alive = True
            status[p_type] = is_alive
        return status

    @staticmethod
    def build_hp_data(world, part_list_comp) -> List[Dict[str, Any]]:
        hp_data = []
        for p_key in BattleViewModel.HP_BAR_ORDER:
            p_id = part_list_comp.parts.get(p_key)
            if p_id is not None:
                h = world.entities[p_id]['health']
                hp_data.append({
                    'key': p_key,
                    'label': PART_LABELS.get(p_key, ""),
                    'current': int(h.display_hp),
                    'max': h.max_hp,
                    'ratio': h.display_hp / h.max_hp if h.max_hp > 0 else 0
                })
        return hp_data


class CutinViewModel:
    """カットイン演出用のデータ生成を担当"""

    @staticmethod
    def build_action_state(world, flow) -> Optional[Dict[str, Any]]:
        """現在の行動イベントからカットイン描画に必要な情報をパッキングする"""
        event_eid = flow.processing_event_id
        if event_eid is None: return None
        
        event_comps = world.try_get_entity(event_eid)
        if not event_comps or 'actionevent' not in event_comps: return None
        
        event = event_comps['actionevent']
        attacker_id = event.attacker_id
        target_id = event.current_target_id
        
        attacker_comps = world.try_get_entity(attacker_id)
        target_comps = world.try_get_entity(target_id)
        if not attacker_comps or not target_comps: return None

        # 攻撃特性
        trait = None
        if event.part_type:
             p_id = attacker_comps['partlist'].parts.get(event.part_type)
             p_comps = world.try_get_entity(p_id)
             if p_comps and 'attack' in p_comps:
                 trait = p_comps['attack'].trait

        # 進行度
        progress = flow.cutin_progress if flow.current_phase == BattlePhase.CUTIN else 1.0

        return {
            'attacker_visual': CutinViewModel.create_character_visual_state(
                CutinViewModel.create_character_data(world, attacker_id),
                BattleViewModel.build_hp_data(world, attacker_comps['partlist']),
                show_hp=False
            ),
            'target_visual': CutinViewModel.create_character_visual_state(
                CutinViewModel.create_character_data(world, target_id),
                BattleViewModel.build_hp_data(world, target_comps['partlist']),
                show_hp=True
            ),
            'progress': progress,
            'trait': trait,
            'result': event.calculation_result,
            'is_enemy': (attacker_comps['team'].team_type == TeamType.ENEMY)
        }

    @staticmethod
    def create_character_data(world, eid: int) -> Dict[str, Any]:
        comps = world.entities[eid]
        return {
            'name': comps['medal'].nickname,
            'color': comps['team'].team_color
        }

    @staticmethod
    def create_character_visual_state(char_data: Dict[str, Any], hp_data: List[Dict[str, Any]], show_hp: bool = True) -> Dict[str, Any]:
        return {
            'color': char_data['color'],
            'is_alive_map': {item['key']: (item['current'] > 0) for item in hp_data},
            'hp_bars': hp_data if show_hp else None
        }