"""HUDやメニューなど、基本的なバトル描画用データの生成ロジック"""

from typing import Dict, Any, List, Optional
from config import COLORS, GAME_PARAMS
from battle.constants import PartType, GaugeStatus, PART_LABELS, TeamType, BattlePhase, MENU_PART_ORDER

class BattleViewModel:
    """HUDや機体アイコン、メニューの描画データを担当"""

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

        from battle.domain.gauge_logic import calculate_current_x
        icon_x = calculate_current_x(pos.x, gauge.status, gauge.progress, team.team_type)
        border_color = BattleViewModel._get_border_color(eid, gauge, flow, context)
        part_status = BattleViewModel._get_part_status_map(world, part_list)
        home_x = pos.x + (GAME_PARAMS['GAUGE_WIDTH'] if team.team_type == TeamType.ENEMY else 0)

        return {
            'id': eid,
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
    def get_active_target_eid(world, context, flow) -> Optional[int]:
        """現在メニューで選択されているパーツのターゲット機体IDを取得"""
        if flow.current_phase != BattlePhase.INPUT:
            return None
            
        eid = context.current_turn_entity_id
        if not eid or eid not in world.entities:
            return None
            
        idx = context.selected_menu_index
        if idx < len(MENU_PART_ORDER):
            p_type = MENU_PART_ORDER[idx]
            target_data = world.entities[eid]['gauge'].part_targets.get(p_type)
            if target_data:
                return target_data[0] # (target_id, part_type)
        return None

    @staticmethod
    def build_action_menu_data(world, eid: int) -> List[Dict[str, Any]]:
        """アクション選択メニューのボタン情報を構築する"""
        comps = world.try_get_entity(eid)
        if not comps: return []
        
        part_list = comps['partlist']
        buttons = []
        
        # パーツ攻撃ボタン
        for p_type in MENU_PART_ORDER:
            p_id = part_list.parts.get(p_type)
            p_comps = world.try_get_entity(p_id) if p_id is not None else None
            
            if p_comps:
                is_alive = p_comps['health'].hp > 0
                buttons.append({
                    'label': p_comps['name'].name,
                    'enabled': is_alive
                })
        
        # スキップボタン
        buttons.append({
            'label': "スキップ",
            'enabled': True
        })
        
        return buttons

    @staticmethod
    def build_hp_data(world, part_list_comp) -> List[Dict[str, Any]]:
        """HPバー表示用のリストデータを構築"""
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