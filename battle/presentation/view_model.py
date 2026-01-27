"""描画用データ（ViewModel）の生成ロジック"""

from typing import Dict, Any, List, Optional, Tuple
from config import COLORS, GAME_PARAMS
from battle.constants import PartType, GaugeStatus, PART_LABELS, TeamType, BattlePhase, MENU_PART_ORDER, TraitType

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

        from battle.domain.utils import calculate_current_x
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
    def get_event_actor_ids(world, flow) -> Tuple[Optional[int], Optional[int]]:
        """現在実行中のイベントにおける (攻撃者ID, 対象者ID) を取得"""
        if flow.current_phase not in [
            BattlePhase.TARGET_INDICATION, BattlePhase.ATTACK_DECLARATION, 
            BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT
        ]:
            return None, None
            
        event_eid = flow.processing_event_id
        event_comps = world.try_get_entity(event_eid)
        if not event_comps or 'actionevent' not in event_comps:
            return None, None
            
        event = event_comps['actionevent']
        return event.attacker_id, event.current_target_id

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
    """カットイン演出用のデータ生成を担当（プレゼンテーション・ロジック）"""

    # 座標計算用定数
    SW = GAME_PARAMS['SCREEN_WIDTH']
    SH = GAME_PARAMS['SCREEN_HEIGHT']
    CENTER_Y = SH // 2 - 20 # 黒帯を考慮した中央付近
    LEFT_POS_X = 150
    RIGHT_POS_X = SW - 150
    OFFSCREEN_OFFSET = 400
    
    # タイミング定義
    T_ENTER = 0.2
    
    MELEE_TIMING = {
        'dash_start': 0.35,
        'hit': 0.55,
        'leave_start': 0.75,
        'impact': 0.55
    }
    
    SHOOTING_TIMING = {
        'switch_start': 0.45,
        'switch_end': 0.7,
        'fire': 0.25,
        'impact': 0.8
    }

    @staticmethod
    def build_action_state(world, flow) -> Optional[Dict[str, Any]]:
        """現在の行動イベントからカットイン描画に必要な情報を計算し、確定済みの描画指示データを返す"""
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

        # 特性の取得
        trait = None
        if event.part_type:
             p_id = attacker_comps['partlist'].parts.get(event.part_type)
             p_comps = world.try_get_entity(p_id)
             if p_comps and 'attack' in p_comps:
                 trait = p_comps['attack'].trait

        # 基本情報の生成
        progress = flow.cutin_progress if flow.current_phase == BattlePhase.CUTIN else 1.0
        is_enemy = (attacker_comps['team'].team_type == TeamType.ENEMY)
        
        # 演出座標計算ロジックの呼び出し
        frame_state = CutinViewModel._calculate_frame_state(progress, trait, is_enemy, event.calculation_result)

        # キャラクター固有の描画リソース(色・HP等)と座標を合成
        frame_state['attacker'].update(CutinViewModel.create_character_visual_state(
            CutinViewModel.create_character_data(world, attacker_id),
            BattleViewModel.build_hp_data(world, attacker_comps['partlist']),
            show_hp=False
        ))
        frame_state['defender'].update(CutinViewModel.create_character_visual_state(
            CutinViewModel.create_character_data(world, target_id),
            BattleViewModel.build_hp_data(world, target_comps['partlist']),
            show_hp=True
        ))
        
        # 共通情報の付加
        frame_state['mirror'] = is_enemy
        frame_state['trait'] = trait

        return frame_state

    @staticmethod
    def _calculate_frame_state(progress, attack_trait, is_enemy, hit_result):
        """進行度に基づき、ピクセル座標やアルファ値を計算する（旧Cinematicsの移植）"""
        
        # 1. 全体フェード
        fade_ratio = min(1.0, progress / CutinViewModel.T_ENTER)
        bg_alpha = int(150 * fade_ratio)
        bar_height = int((CutinViewModel.SH // 8) * fade_ratio)

        # 2. 座標計算
        is_melee = (attack_trait in TraitType.MELEE_TRAITS)
        if is_melee:
            char_state = CutinViewModel._calc_melee_positions(progress)
            t_impact = CutinViewModel.MELEE_TIMING['impact']
        else:
            char_state = CutinViewModel._calc_shooting_positions(progress, hit_result, attack_trait)
            t_impact = CutinViewModel.SHOOTING_TIMING['impact']

        # 3. ポップアップ
        popup_state = CutinViewModel._calc_popup_state(progress, t_impact, hit_result)

        # 4. ミラーリング（攻撃者がエネミーの場合）
        if is_enemy:
            char_state['attacker']['x'] = CutinViewModel.SW - char_state['attacker']['x']
            char_state['defender']['x'] = CutinViewModel.SW - char_state['defender']['x']
            if char_state['bullet']['visible']:
                char_state['bullet']['x'] = CutinViewModel.SW - char_state['bullet']['x']

        return {
            'bg_alpha': bg_alpha,
            'bar_height': bar_height,
            'attacker': char_state['attacker'],
            'defender': char_state['defender'],
            'bullet': char_state['bullet'],
            'effect': char_state['effect'],
            'popup': popup_state
        }

    @staticmethod
    def _calc_melee_positions(progress):
        t = CutinViewModel.MELEE_TIMING
        atk = {'x': -1000, 'y': CutinViewModel.CENTER_Y, 'visible': True}
        defn = {'x': CutinViewModel.SW + 1000, 'y': CutinViewModel.CENTER_Y, 'visible': True}
        eff = {'visible': False, 'x': 0, 'y': 0, 'progress': progress, 'start_time': t['hit']}
        
        if progress < CutinViewModel.T_ENTER:
            ratio = progress / CutinViewModel.T_ENTER
            atk['y'] = (CutinViewModel.CENTER_Y + 400) - (400 * ratio)
            atk['x'] = CutinViewModel.LEFT_POS_X
        elif progress < t['dash_start']:
            atk['x'] = CutinViewModel.LEFT_POS_X
        elif progress < t['hit']:
            ratio = (progress - t['dash_start']) / (t['hit'] - t['dash_start'])
            target_x = CutinViewModel.RIGHT_POS_X - 100
            atk['x'] = CutinViewModel.LEFT_POS_X + (target_x - CutinViewModel.LEFT_POS_X) * (ratio * ratio)
        elif progress < t['leave_start']:
            atk['x'] = CutinViewModel.RIGHT_POS_X - 100
            eff['visible'] = True
            eff['x'], eff['y'] = CutinViewModel.RIGHT_POS_X, CutinViewModel.CENTER_Y
        else:
            ratio = (progress - t['leave_start']) / (1.0 - t['leave_start'])
            start_x = CutinViewModel.RIGHT_POS_X - 100
            target_x = CutinViewModel.SW + CutinViewModel.OFFSCREEN_OFFSET
            atk['x'] = start_x + (target_x - start_x) * (ratio * ratio)

        if progress < CutinViewModel.T_ENTER:
            ratio = progress / CutinViewModel.T_ENTER
            defn['y'] = (CutinViewModel.CENTER_Y - 400) + (400 * ratio)
            defn['x'] = CutinViewModel.RIGHT_POS_X
        else:
            defn['x'] = CutinViewModel.RIGHT_POS_X
        
        return {'attacker': atk, 'defender': defn, 'bullet': {'visible': False}, 'effect': eff}

    @staticmethod
    def _calc_shooting_positions(progress, hit_result, trait):
        t = CutinViewModel.SHOOTING_TIMING
        atk = {'x': -1000, 'y': CutinViewModel.CENTER_Y, 'visible': True}
        defn = {'x': CutinViewModel.SW + 1000, 'y': CutinViewModel.CENTER_Y, 'visible': True}
        bul = {'visible': False, 'x': 0, 'y': CutinViewModel.CENTER_Y, 'type': trait}

        if progress < t['switch_start']:
            if progress < CutinViewModel.T_ENTER:
                ratio = progress / CutinViewModel.T_ENTER
                atk['y'] = (CutinViewModel.CENTER_Y + 400) - (400 * ratio)
                atk['x'] = CutinViewModel.LEFT_POS_X
            else:
                atk['x'] = CutinViewModel.LEFT_POS_X
        elif progress < t['switch_end']:
            ratio = (progress - t['switch_start']) / (t['switch_end'] - t['switch_start'])
            atk['x'] = CutinViewModel.LEFT_POS_X - (CutinViewModel.LEFT_POS_X + CutinViewModel.OFFSCREEN_OFFSET) * ratio
        else:
            atk['x'] = -CutinViewModel.OFFSCREEN_OFFSET * 2

        if progress >= t['switch_start'] and progress < t['switch_end']:
            ratio = (progress - t['switch_start']) / (t['switch_end'] - t['switch_start'])
            start_x = CutinViewModel.SW + CutinViewModel.OFFSCREEN_OFFSET
            defn['x'] = start_x - (start_x - CutinViewModel.RIGHT_POS_X) * ratio
        elif progress >= t['switch_end']:
            defn['x'] = CutinViewModel.RIGHT_POS_X

        if progress >= t['fire']:
            bul['visible'] = True
            sc_x = CutinViewModel.SW // 2
            if progress < t['switch_start']:
                ratio = (progress - t['fire']) / (t['switch_start'] - t['fire'])
                start_x = CutinViewModel.LEFT_POS_X + 80
                bul['x'] = start_x + (sc_x - start_x) * ratio
            elif progress < t['switch_end']:
                ratio = (progress - t['switch_start']) / (t['switch_end'] - t['switch_start'])
                bul['x'] = sc_x + (50 * ratio)
            else:
                ratio = (progress - t['switch_end']) / (t['impact'] - t['switch_end'])
                target_hit_x = CutinViewModel.RIGHT_POS_X
                if progress <= t['impact']:
                    bul['x'] = (sc_x + 50) + (target_hit_x - (sc_x + 50)) * ratio
                else:
                    is_hit = hit_result.is_hit if hit_result else False
                    if is_hit: bul['visible'] = False
                    else:
                        miss_r = (progress - t['impact']) / (1.0 - t['impact'])
                        bul['x'] = target_hit_x + (CutinViewModel.SW - target_hit_x + 100) * miss_r

        return {'attacker': atk, 'defender': defn, 'bullet': bul, 'effect': {'visible': False}}

    @staticmethod
    def _calc_popup_state(progress, t_impact, hit_result):
        if progress <= t_impact or not hit_result:
            return {'visible': False}
        anim_t = min(1.0, (progress - t_impact) / (1.0 - t_impact))
        return {
            'visible': True,
            'x': CutinViewModel.RIGHT_POS_X,
            'y': CutinViewModel.CENTER_Y - 60 - (40 * anim_t),
            'result': hit_result
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