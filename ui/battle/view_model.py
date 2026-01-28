"""ECSからSnapshotへの変換ロジック（ViewModel）"""

from typing import Dict, Any, List, Optional, Tuple
from config import GAME_PARAMS, COLORS
from battle.constants import BattlePhase, BattleTiming, PART_LABELS, MENU_PART_ORDER
from domain.constants import GaugeStatus, TeamType, PartType, TraitType
from domain.gauge_logic import calculate_gauge_ratio
from .snapshot import (
    BattleStateSnapshot, CharacterViewData, LogWindowData, 
    ActionMenuData, ActionButtonData, GameOverData, CutinStateData
)

class BattleViewModel:
    """Worldの状態を解析し、描画用の不変なデータ（Snapshot）に変換する"""
    
    # 演出タイミング定数
    T_ENTER = 0.2
    # 格闘用
    T_MELEE_DASH = 0.35
    T_MELEE_HIT = 0.55
    T_MELEE_LEAVE = 0.75
    # 射撃用
    T_SHOOT_FIRE = 0.25
    T_SHOOT_SWAP_START = 0.45
    T_SHOOT_SWAP_END = 0.7
    T_SHOOT_IMPACT = 0.8

    def __init__(self, world):
        self.world = world

    def create_snapshot(self) -> BattleStateSnapshot:
        context, flow = self._get_battle_state()
        if not context or not flow: return BattleStateSnapshot()

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
        return (entities[0][1]['battlecontext'], entities[0][1]['battleflow']) if entities else (None, None)

    def _build_character_data(self, context, flow) -> Dict[int, CharacterViewData]:
        chars = {}
        for eid, comps in self.world.get_entities_with_components('render', 'position', 'gauge', 'partlist', 'team', 'medal'):
            g, team = comps['gauge'], comps['team']
            icon_x = self._calculate_current_icon_x(comps['position'].x, g, team.team_type)
            home_x = comps['position'].x + (GAME_PARAMS['GAUGE_WIDTH'] if team.team_type == TeamType.ENEMY else 0)

            chars[eid] = CharacterViewData(
                entity_id=eid, x=comps['position'].x, y=comps['position'].y,
                icon_x=icon_x, home_x=home_x, home_y=comps['position'].y,
                team_color=team.team_color, name=comps['medal'].nickname,
                border_color=self._get_border_color(eid, g, flow, context),
                part_status=self._get_part_status_map(comps['partlist'])
            )
        return chars

    def _calculate_current_icon_x(self, base_x: int, gauge, team_type: str) -> float:
        center_x, offset = GAME_PARAMS['SCREEN_WIDTH'] // 2, 40
        ratio = calculate_gauge_ratio(gauge.status, gauge.progress)
        
        if team_type == TeamType.PLAYER:
            return base_x + ratio * ((center_x - offset) - base_x)
        else:
            start_x = base_x + GAME_PARAMS['GAUGE_WIDTH']
            return start_x + ratio * ((center_x + offset) - start_x)

    def _get_border_color(self, eid, gauge, flow, context):
        if eid == flow.active_actor_id or eid in context.waiting_queue or gauge.status == GaugeStatus.ACTION_CHOICE:
            return COLORS.get('BORDER_WAIT')
        if gauge.status == GaugeStatus.CHARGING: return COLORS.get('BORDER_CHARGE')
        if gauge.status == GaugeStatus.COOLDOWN: return COLORS.get('BORDER_COOLDOWN')
        return None

    def _get_part_status_map(self, part_list_comp) -> Dict[str, bool]:
        return {pt: (self.world.entities[pid]['health'].hp > 0) 
                for pt, pid in part_list_comp.parts.items()}

    def _get_active_target_eid(self, context, flow) -> Optional[int]:
        if flow.current_phase != BattlePhase.INPUT: return None
        eid = context.current_turn_entity_id
        if not eid: return None
        
        idx = context.selected_menu_index
        if idx < len(MENU_PART_ORDER):
            p_type = MENU_PART_ORDER[idx]
            target_data = self.world.entities[eid]['gauge'].part_targets.get(p_type)
            if target_data: return target_data[0]
        return None

    def _build_target_line(self, characters, flow):
        if flow.current_phase != BattlePhase.TARGET_INDICATION: return None
        event = self.world.try_get_entity(flow.processing_event_id).get('actionevent')
        if not event: return None
            
        atk_id, tgt_id = event.attacker_id, event.current_target_id
        if atk_id in characters and tgt_id in characters:
            elapsed = max(0, BattleTiming.TARGET_INDICATION - flow.phase_timer)
            return (characters[atk_id], characters[tgt_id], elapsed)
        return None

    def _build_log_window(self, context, flow) -> LogWindowData:
        show_guide = flow.current_phase in [BattlePhase.LOG_WAIT, BattlePhase.ATTACK_DECLARATION, BattlePhase.CUTIN_RESULT]
        logs = [] if flow.current_phase in [BattlePhase.CUTIN, BattlePhase.CUTIN_RESULT] else context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:]
        return LogWindowData(logs=logs, show_input_guidance=show_guide, is_active=True)

    def _build_action_menu(self, context, flow) -> ActionMenuData:
        if flow.current_phase != BattlePhase.INPUT: return ActionMenuData(is_active=False)
        comps = self.world.try_get_entity(context.current_turn_entity_id)
        if not comps: return ActionMenuData(is_active=False)

        buttons = []
        for p_type in MENU_PART_ORDER:
            p_id = comps['partlist'].parts.get(p_type)
            p_comps = self.world.try_get_entity(p_id)
            if p_comps:
                buttons.append(ActionButtonData(label=p_comps['name'].name, enabled=p_comps['health'].hp > 0))
        buttons.append(ActionButtonData(label="スキップ", enabled=True))
        
        return ActionMenuData(actor_name=comps['medal'].nickname, buttons=buttons, 
                              selected_index=context.selected_menu_index, is_active=True)

    def _build_game_over(self, flow) -> GameOverData:
        return GameOverData(winner=flow.winner or "", is_active=(flow.current_phase == BattlePhase.GAME_OVER))

    def _build_cutin_state(self, flow) -> CutinStateData:
        event = self.world.try_get_entity(flow.processing_event_id).get('actionevent')
        atk_comps = self.world.try_get_entity(event.attacker_id)
        tgt_comps = self.world.try_get_entity(event.current_target_id)
        if not atk_comps or not tgt_comps: return CutinStateData(False)

        trait = None
        p_id = atk_comps['partlist'].parts.get(event.part_type)
        p_comps = self.world.try_get_entity(p_id)
        if p_comps and 'attack' in p_comps: trait = p_comps['attack'].trait

        progress = flow.cutin_progress if flow.current_phase == BattlePhase.CUTIN else 1.0
        is_enemy = (atk_comps['team'].team_type == TeamType.ENEMY)
        
        state = self._calculate_cutin_frame(progress, trait, is_enemy, event.calculation_result)
        state.attacker.update(self._create_char_visual(atk_comps, show_hp=False))
        state.defender.update(self._create_char_visual(tgt_comps, show_hp=True))
        state.mirror, state.bullet['type'], state.is_active = is_enemy, trait, True
        return state

    def _create_char_visual(self, comps, show_hp):
        hp_bars = []
        part_list = comps['partlist']
        for p_key in [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM, PartType.LEGS]:
            p_id = part_list.parts.get(p_key)
            if p_id is not None:
                h = self.world.entities[p_id]['health']
                hp_bars.append({'key': p_key, 'label': PART_LABELS.get(p_key, ""), 'current': int(h.display_hp),
                                'max': h.max_hp, 'ratio': h.display_hp / h.max_hp if h.max_hp > 0 else 0})
        return {'color': comps['team'].team_color, 'is_alive_map': {it['key']: (it['current'] > 0) for it in hp_bars},
                'hp_bars': hp_bars if show_hp else None}

    def _calculate_cutin_frame(self, progress, trait, is_enemy, hit_result):
        sw, sh = GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']
        cy = sh // 2 - 20
        
        fade_ratio = min(1.0, progress / self.T_ENTER)
        state = CutinStateData(bg_alpha=int(150 * fade_ratio), bar_height=int((sh // 8) * fade_ratio))

        if trait in TraitType.MELEE_TRAITS:
            self._calc_melee_sequence(state, progress, sw, cy)
        else:
            self._calc_shoot_sequence(state, progress, sw, cy, hit_result)

        # ポップアップ判定
        impact_t = self.T_MELEE_HIT if trait in TraitType.MELEE_TRAITS else self.T_SHOOT_IMPACT
        if progress > impact_t and hit_result:
            anim_t = min(1.0, (progress - impact_t) / (1.0 - impact_t))
            state.popup = {'visible': True, 'x': sw - 150, 'y': cy - 60 - (40 * anim_t), 'result': hit_result}

        if is_enemy:
            for d in [state.attacker, state.defender, state.bullet]:
                if 'x' in d: d['x'] = sw - d['x']
        return state

    def _calc_melee_sequence(self, state, progress, sw, cy):
        l_x, r_x, off = 150, sw - 150, 400
        atk, defn = {'y': cy, 'visible': True}, {'x': r_x, 'y': cy, 'visible': True}
        
        if progress < self.T_ENTER:
            r = progress / self.T_ENTER
            atk['x'], atk['y'] = l_x, (cy + off) - (off * r)
            defn['y'] = (cy - off) + (off * r)
        elif progress < self.T_MELEE_DASH:
            atk['x'] = l_x
        elif progress < self.T_MELEE_HIT:
            r = (progress - self.T_MELEE_DASH) / (self.T_MELEE_HIT - self.T_MELEE_DASH)
            atk['x'] = l_x + (r_x - 100 - l_x) * (r * r)
        elif progress < self.T_MELEE_LEAVE:
            atk['x'] = r_x - 100
            state.effect = {'visible': True, 'x': r_x, 'y': cy, 'progress': progress, 'start_time': self.T_MELEE_HIT}
        else:
            r = (progress - self.T_MELEE_LEAVE) / (1.0 - self.T_MELEE_LEAVE)
            atk['x'] = (r_x - 100) + (sw + off - (r_x - 100)) * (r * r)
            
        state.attacker, state.defender = atk, defn

    def _calc_shoot_sequence(self, state, progress, sw, cy, hit_result):
        l_x, r_x, off = 150, sw - 150, 400
        atk, defn = {'y': cy, 'visible': True}, {'y': cy, 'visible': True},
        bul = {'visible': False, 'x': 0, 'y': cy}

        # アタッカー退場 & ディフェンダー入場
        if progress < self.T_SHOOT_SWAP_START:
            atk['x'] = l_x
            if progress < self.T_ENTER:
                r = progress / self.T_ENTER
                atk['y'], defn['x'] = (cy + off) - (off * r), sw + off
            else:
                defn['x'] = sw + off
        elif progress < self.T_SHOOT_SWAP_END:
            r = (progress - self.T_SHOOT_SWAP_START) / (self.T_SHOOT_SWAP_END - self.T_SHOOT_SWAP_START)
            atk['x'], defn['x'] = l_x - (l_x + off) * r, (sw + off) - (sw + off - r_x) * r
        else:
            atk['x'], defn['x'] = -off * 2, r_x

        # 弾丸
        if progress >= self.T_SHOOT_FIRE:
            bul['visible'] = True
            mid_x = sw // 2
            if progress < self.T_SHOOT_SWAP_START:
                r = (progress - self.T_SHOOT_FIRE) / (self.T_SHOOT_SWAP_START - self.T_SHOOT_FIRE)
                bul['x'] = (l_x + 80) + (mid_x - (l_x + 80)) * r
            elif progress < self.T_SHOOT_SWAP_END:
                r = (progress - self.T_SHOOT_SWAP_START) / (self.T_SHOOT_SWAP_END - self.T_SHOOT_SWAP_START)
                bul['x'] = mid_x + (50 * r)
            else:
                r = (progress - self.T_SHOOT_SWAP_END) / (self.T_SHOOT_IMPACT - self.T_SHOOT_SWAP_END)
                if progress <= self.T_SHOOT_IMPACT:
                    bul['x'] = (mid_x + 50) + (r_x - (mid_x + 50)) * r
                else:
                    if hit_result and hit_result.is_hit: bul['visible'] = False
                    else:
                        r_miss = (progress - self.T_SHOOT_IMPACT) / (1.0 - self.T_SHOOT_IMPACT)
                        bul['x'] = r_x + (sw - r_x + 100) * r_miss

        state.attacker, state.defender, state.bullet = atk, defn, bul