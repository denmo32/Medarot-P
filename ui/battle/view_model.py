"""ECSからSnapshotへの変換ロジック（ViewModel）"""

from typing import Dict, Any, List, Optional, Tuple
from config import GAME_PARAMS, COLORS
from battle.constants import (
    BattlePhase, BattleTiming, PART_LABELS, MENU_PART_ORDER
)
from domain.constants import (
    GaugeStatus, TeamType, PartType, TraitType
)
from domain.gauge_logic import calculate_gauge_ratio
from .snapshot import (
    BattleStateSnapshot, CharacterViewData, LogWindowData, 
    ActionMenuData, ActionButtonData, GameOverData, CutinStateData
)

class BattleViewModel:
    """Worldの状態を読み取り、BattleStateSnapshotを生成するクラス"""
    
    def __init__(self, world):
        self.world = world

    def create_snapshot(self) -> BattleStateSnapshot:
        context, flow = self._get_battle_state()
        if not context or not flow:
            return BattleStateSnapshot()

        snapshot = BattleStateSnapshot()
        snapshot.characters = self._build_character_data(context, flow)
        snapshot.target_marker_eid = self._get_active_target_eid(context, flow)
        snapshot.target_line = self._build_target_line(snapshot.characters, flow)
        snapshot.log_window = self._build_log_window(context, flow)
        snapshot.action_menu = self._build_action_menu(context, flow)
        snapshot.game_over = self._build_game_over(flow)

        if flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT]:
            snapshot.cutin = self._build_cutin_state(flow)
        
        return snapshot

    def _get_battle_state(self):
        entities = self.world.get_entities_with_components('battlecontext', 'battleflow')
        if not entities: return None, None
        return entities[0][1]['battlecontext'], entities[0][1]['battleflow']

    def _build_character_data(self, context, flow) -> Dict[int, CharacterViewData]:
        chars = {}
        for eid, comps in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'medal'):
            pos = comps['position']
            gauge = comps['gauge']
            team = comps['team']
            medal = comps['medal']
            part_list = comps['partlist']

            icon_x = self._calculate_current_icon_x(pos.x, gauge, team.team_type)
            
            border_color = self._get_border_color(eid, gauge, flow, context)
            part_status = self._get_part_status_map(part_list)
            home_x = pos.x + (GAME_PARAMS['GAUGE_WIDTH'] if team.team_type == TeamType.ENEMY else 0)

            chars[eid] = CharacterViewData(
                entity_id=eid,
                x=pos.x,
                y=pos.y,
                icon_x=icon_x,
                home_x=home_x,
                home_y=pos.y,
                team_color=team.team_color,
                name=medal.nickname,
                border_color=border_color,
                part_status=part_status
            )
        return chars

    def _calculate_current_icon_x(self, base_x: int, gauge, team_type: str) -> float:
        center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
        offset = 40
        ratio = calculate_gauge_ratio(gauge.status, gauge.progress)
        
        if team_type == TeamType.PLAYER:
            target_x = center_x - offset
            return base_x + ratio * (target_x - base_x)
        else:
            start_x = base_x + GAME_PARAMS['GAUGE_WIDTH']
            target_x = center_x + offset
            return start_x + ratio * (target_x - start_x)

    def _get_border_color(self, eid, gauge, flow, context):
        if eid == flow.active_actor_id or eid in context.waiting_queue or gauge.status == GaugeStatus.ACTION_CHOICE:
            return COLORS.get('BORDER_WAIT')
        if gauge.status == GaugeStatus.CHARGING:
            return COLORS.get('BORDER_CHARGE')
        if gauge.status == GaugeStatus.COOLDOWN:
            return COLORS.get('BORDER_COOLDOWN')
        return None

    def _get_part_status_map(self, part_list_comp) -> Dict[str, bool]:
        status = {}
        for p_type in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]:
            p_id = part_list_comp.parts.get(p_type)
            is_alive = False
            if p_id:
                hp = self.world.entities[p_id]['health'].hp
                if hp > 0:
                    is_alive = True
            status[p_type] = is_alive
        return status

    def _get_active_target_eid(self, context, flow) -> Optional[int]:
        if flow.current_phase != BattlePhase.INPUT:
            return None
            
        eid = context.current_turn_entity_id
        if not eid or eid not in self.world.entities:
            return None
            
        idx = context.selected_menu_index
        if idx < len(MENU_PART_ORDER):
            p_type = MENU_PART_ORDER[idx]
            target_data = self.world.entities[eid]['gauge'].part_targets.get(p_type)
            if target_data:
                return target_data[0]
        return None

    def _build_target_line(self, characters, flow):
        if flow.current_phase != BattlePhase.TARGET_INDICATION:
            return None
        
        event_eid = flow.processing_event_id
        event_comps = self.world.try_get_entity(event_eid)
        if not event_comps or 'actionevent' not in event_comps:
            return None
            
        event = event_comps['actionevent']
        atk_id, tgt_id = event.attacker_id, event.current_target_id
        
        if atk_id in characters and tgt_id in characters:
            elapsed = max(0, BattleTiming.TARGET_INDICATION - flow.phase_timer)
            return (characters[atk_id], characters[tgt_id], elapsed)
        return None

    def _build_log_window(self, context, flow) -> LogWindowData:
        show_guide = flow.current_phase in [BattlePhase.LOG_WAIT, BattlePhase.ATTACK_DECLARATION, BattlePhase.CUTIN_RESULT]
        logs = [] if flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT] else context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:]
        
        return LogWindowData(
            logs=logs,
            show_input_guidance=show_guide,
            is_active=True
        )

    def _build_action_menu(self, context, flow) -> ActionMenuData:
        is_active = (flow.current_phase == BattlePhase.INPUT)
        if not is_active:
            return ActionMenuData("", [], 0, False)

        eid = context.current_turn_entity_id
        if not eid: return ActionMenuData("", [], 0, False)
        
        comps = self.world.try_get_entity(eid)
        if not comps: return ActionMenuData("", [], 0, False)

        part_list = comps['partlist']
        buttons = []
        
        for p_type in MENU_PART_ORDER:
            p_id = part_list.parts.get(p_type)
            p_comps = self.world.try_get_entity(p_id) if p_id is not None else None
            is_alive = False
            label = ""
            if p_comps:
                is_alive = p_comps['health'].hp > 0
                label = p_comps['name'].name
            buttons.append(ActionButtonData(label=label, enabled=is_alive))
        
        buttons.append(ActionButtonData(label="スキップ", enabled=True))
        
        return ActionMenuData(
            actor_name=comps['medal'].nickname,
            buttons=buttons,
            selected_index=context.selected_menu_index,
            is_active=True
        )

    def _build_game_over(self, flow) -> GameOverData:
        return GameOverData(
            winner=flow.winner or "",
            is_active=(flow.current_phase == BattlePhase.GAME_OVER)
        )

    def _build_cutin_state(self, flow) -> CutinStateData:
        event_eid = flow.processing_event_id
        if event_eid is None: return CutinStateData(False)
        
        event_comps = self.world.try_get_entity(event_eid)
        if not event_comps or 'actionevent' not in event_comps: return CutinStateData(False)
        
        event = event_comps['actionevent']
        attacker_id = event.attacker_id
        target_id = event.current_target_id
        
        attacker_comps = self.world.try_get_entity(attacker_id)
        target_comps = self.world.try_get_entity(target_id)
        if not attacker_comps or not target_comps: return CutinStateData(False)

        trait = None
        if event.part_type:
             p_id = attacker_comps['partlist'].parts.get(event.part_type)
             p_comps = self.world.try_get_entity(p_id)
             if p_comps and 'attack' in p_comps:
                 trait = p_comps['attack'].trait

        progress = flow.cutin_progress if flow.current_phase == BattlePhase.CUTIN else 1.0
        is_enemy = (attacker_comps['team'].team_type == TeamType.ENEMY)
        
        state = self._calculate_cutin_frame(progress, trait, is_enemy, event.calculation_result)
        
        state.attacker.update(self._create_char_visual(attacker_id, attacker_comps, show_hp=False))
        state.defender.update(self._create_char_visual(target_id, target_comps, show_hp=True))
        
        state.mirror = is_enemy
        state.bullet['type'] = trait
        state.is_active = True
        
        return state

    def _create_char_visual(self, eid, comps, show_hp):
        hp_data = []
        part_list = comps['partlist']
        for p_key in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]:
            p_id = part_list.parts.get(p_key)
            if p_id is not None:
                h = self.world.entities[p_id]['health']
                hp_data.append({
                    'key': p_key,
                    'label': PART_LABELS.get(p_key, ""),
                    'current': int(h.display_hp),
                    'max': h.max_hp,
                    'ratio': h.display_hp / h.max_hp if h.max_hp > 0 else 0
                })
        
        return {
            'color': comps['team'].team_color,
            'is_alive_map': {item['key']: (item['current'] > 0) for item in hp_data},
            'hp_bars': hp_data if show_hp else None
        }

    def _calculate_cutin_frame(self, progress, attack_trait, is_enemy, hit_result):
        SW = GAME_PARAMS['SCREEN_WIDTH']
        SH = GAME_PARAMS['SCREEN_HEIGHT']
        CENTER_Y = SH // 2 - 20
        LEFT_POS_X = 150
        RIGHT_POS_X = SW - 150
        OFFSCREEN = 400
        T_ENTER = 0.2

        fade_ratio = min(1.0, progress / T_ENTER)
        bg_alpha = int(150 * fade_ratio)
        bar_height = int((SH // 8) * fade_ratio)

        is_melee = (attack_trait in TraitType.MELEE_TRAITS)
        
        if is_melee:
            t_dash = 0.35
            t_hit = 0.55
            t_leave = 0.75
            
            atk = {'x': -1000, 'y': CENTER_Y, 'visible': True}
            defn = {'x': SW + 1000, 'y': CENTER_Y, 'visible': True}
            eff = {'visible': False, 'x': 0, 'y': 0, 'progress': progress, 'start_time': t_hit}
            bul = {'visible': False}

            if progress < T_ENTER:
                r = progress / T_ENTER
                atk['y'] = (CENTER_Y + 400) - (400 * r)
                atk['x'] = LEFT_POS_X
            elif progress < t_dash:
                atk['x'] = LEFT_POS_X
            elif progress < t_hit:
                r = (progress - t_dash) / (t_hit - t_dash)
                atk['x'] = LEFT_POS_X + (RIGHT_POS_X - 100 - LEFT_POS_X) * (r * r)
            elif progress < t_leave:
                atk['x'] = RIGHT_POS_X - 100
                eff['visible'] = True
                eff['x'], eff['y'] = RIGHT_POS_X, CENTER_Y
            else:
                r = (progress - t_leave) / (1.0 - t_leave)
                atk['x'] = (RIGHT_POS_X - 100) + (SW + OFFSCREEN - (RIGHT_POS_X - 100)) * (r * r)

            if progress < T_ENTER:
                r = progress / T_ENTER
                defn['y'] = (CENTER_Y - 400) + (400 * r)
                defn['x'] = RIGHT_POS_X
            else:
                defn['x'] = RIGHT_POS_X

        else:
            t_sw_start = 0.45
            t_sw_end = 0.7
            t_fire = 0.25
            t_impact = 0.8
            
            atk = {'x': -1000, 'y': CENTER_Y, 'visible': True}
            defn = {'x': SW + 1000, 'y': CENTER_Y, 'visible': True}
            bul = {'visible': False, 'x': 0, 'y': CENTER_Y}
            eff = {'visible': False}

            if progress < t_sw_start:
                if progress < T_ENTER:
                    r = progress / T_ENTER
                    atk['y'] = (CENTER_Y + 400) - (400 * r)
                    atk['x'] = LEFT_POS_X
                else:
                    atk['x'] = LEFT_POS_X
            elif progress < t_sw_end:
                r = (progress - t_sw_start) / (t_sw_end - t_sw_start)
                atk['x'] = LEFT_POS_X - (LEFT_POS_X + OFFSCREEN) * r
            else:
                atk['x'] = -OFFSCREEN * 2

            if progress >= t_sw_start and progress < t_sw_end:
                r = (progress - t_sw_start) / (t_sw_end - t_sw_start)
                start_x = SW + OFFSCREEN
                defn['x'] = start_x - (start_x - RIGHT_POS_X) * r
            elif progress >= t_sw_end:
                defn['x'] = RIGHT_POS_X

            if progress >= t_fire:
                bul['visible'] = True
                sc_x = SW // 2
                if progress < t_sw_start:
                    r = (progress - t_fire) / (t_sw_start - t_fire)
                    bul['x'] = (LEFT_POS_X + 80) + (sc_x - (LEFT_POS_X + 80)) * r
                elif progress < t_sw_end:
                    r = (progress - t_sw_start) / (t_sw_end - t_sw_start)
                    bul['x'] = sc_x + (50 * r)
                else:
                    r = (progress - t_sw_end) / (t_impact - t_sw_end)
                    if progress <= t_impact:
                        bul['x'] = (sc_x + 50) + (RIGHT_POS_X - (sc_x + 50)) * r
                    else:
                        is_hit = hit_result.is_hit if hit_result else False
                        if is_hit: bul['visible'] = False
                        else:
                            r_miss = (progress - t_impact) / (1.0 - t_impact)
                            bul['x'] = RIGHT_POS_X + (SW - RIGHT_POS_X + 100) * r_miss

        popup = {'visible': False}
        impact_time = t_impact if not is_melee else 0.55
        if progress > impact_time and hit_result:
            anim_t = min(1.0, (progress - impact_time) / (1.0 - impact_time))
            popup = {
                'visible': True,
                'x': RIGHT_POS_X,
                'y': CENTER_Y - 60 - (40 * anim_t),
                'result': hit_result
            }

        if is_enemy:
            atk['x'] = SW - atk['x']
            defn['x'] = SW - defn['x']
            if bul.get('visible'):
                bul['x'] = SW - bul['x']

        return CutinStateData(
            is_active=True,
            bg_alpha=bg_alpha,
            bar_height=bar_height,
            attacker=atk,
            defender=defn,
            bullet=bul,
            effect=eff,
            popup=popup
        )