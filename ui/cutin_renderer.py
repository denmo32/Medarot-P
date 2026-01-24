"""カットイン演出管理システム"""

import pygame
import math
from config import GAME_PARAMS
from battle.constants import PartType, TraitType
from .base_renderer import BaseRenderer

class CutinCinematics:
    """
    カットイン演出の計算ロジックを担当するクラス。
    """
    def __init__(self):
        # 画面サイズ等の定数
        self.sw = GAME_PARAMS['SCREEN_WIDTH']
        self.sh = GAME_PARAMS['SCREEN_HEIGHT']
        
        # ウィンドウエリア定義
        self.w_w, self.w_h = 700, 200
        self.w_x, self.w_y = (self.sw - self.w_w) // 2, (self.sh - self.w_h) // 2
        self.center_y = self.w_y + 80
        
        # 左右の基準X座標
        self.left_pos_x = self.w_x + 100
        self.right_pos_x = self.w_x + self.w_w - 100
        
        # オフセット設定
        self.offscreen_offset = 400
        self.bottom_offset = 400
        self.top_offset = 400
        
        # タイミング定義
        self.t_enter = 0.2
        
        # 近接攻撃用タイミング
        self.melee_timing = {
            'dash_start': 0.35,
            'hit': 0.55,
            'leave_start': 0.75,
            'impact': 0.55
        }
        
        # 射撃用タイミング
        self.shooting_timing = {
            'switch_start': 0.45,
            'switch_end': 0.7,
            'fire': 0.25,
            'impact': 0.8
        }

    def calculate_frame_state(self, progress, attack_trait, mirror, hit_result):
        """現在の進行度に基づき、全オブジェクトの状態を計算して辞書で返す"""
        
        # 1. 全体フェード/背景状態
        fade_ratio = min(1.0, progress / self.t_enter) if self.t_enter > 0 else 1.0
        bg_alpha = int(150 * fade_ratio)
        
        # 黒帯の高さ
        target_bar_h = self.sh // 8
        bar_height = int(target_bar_h * fade_ratio)

        # 2. アクション別座標計算
        is_melee = (attack_trait in TraitType.MELEE_TRAITS)
        
        if is_melee:
            char_state = self._calc_melee_positions(progress)
            # 格闘の場合はポップアップタイミングが早い
            t_impact = self.melee_timing['impact']
        else:
            char_state = self._calc_shooting_positions(progress, hit_result, attack_trait)
            t_impact = self.shooting_timing['impact']

        # 3. 結果ポップアップの状態
        popup_state = self._calc_popup_state(progress, t_impact, hit_result)

        # 4. ミラーリング適用
        if mirror:
            self._apply_mirror(char_state, self.sw)

        return {
            'bg_alpha': bg_alpha,
            'bar_height': bar_height,
            'attacker': char_state['attacker'],
            'defender': char_state['defender'],
            'bullet': char_state['bullet'],
            'effect': char_state['effect'],
            'popup': popup_state
        }

    def _calc_melee_positions(self, progress):
        """近接攻撃時の各座標計算"""
        t = self.melee_timing
        
        # 初期値
        atk = {'x': -1000, 'y': self.center_y, 'visible': True}
        defn = {'x': self.sw + 1000, 'y': self.center_y, 'visible': True}
        eff = {'visible': False, 'x': 0, 'y': 0, 'progress': 0.0}
        
        # A. 攻撃側
        if progress < self.t_enter:
            # 登場 (下から)
            ratio = progress / self.t_enter
            atk['y'] = (self.center_y + self.bottom_offset) - (self.bottom_offset * ratio)
            atk['x'] = self.left_pos_x
        elif progress < t['dash_start']:
            # 溜め
            atk['x'] = self.left_pos_x
        elif progress < t['hit']:
            # 急接近
            ratio = (progress - t['dash_start']) / (t['hit'] - t['dash_start'])
            ratio = ratio * ratio # Ease-In
            target_x = self.right_pos_x - 100
            atk['x'] = self.left_pos_x + (target_x - self.left_pos_x) * ratio
        elif progress < t['leave_start']:
            # ヒット中
            atk['x'] = self.right_pos_x - 100
            
            # エフェクト有効化
            eff['visible'] = True
            eff['x'] = self.right_pos_x
            eff['y'] = self.center_y
            eff['progress'] = progress
            eff['start_time'] = t['hit']
        else:
            # 離脱
            ratio = (progress - t['leave_start']) / (1.0 - t['leave_start'])
            ratio = ratio * ratio
            start_x = self.right_pos_x - 100
            target_x = self.sw + self.offscreen_offset
            atk['x'] = start_x + (target_x - start_x) * ratio

        # B. 防御側
        if progress < self.t_enter:
            ratio = progress / self.t_enter
            defn['y'] = (self.center_y - self.top_offset) + (self.top_offset * ratio)
            defn['x'] = self.right_pos_x
        else:
            defn['x'] = self.right_pos_x
        
        return {'attacker': atk, 'defender': defn, 'bullet': {'visible': False}, 'effect': eff}

    def _calc_shooting_positions(self, progress, hit_result, trait):
        """射撃攻撃時の各座標計算"""
        t = self.shooting_timing
        
        atk = {'x': -1000, 'y': self.center_y, 'visible': True}
        defn = {'x': self.sw + 1000, 'y': self.center_y, 'visible': True}
        bul = {'visible': False, 'x': 0, 'y': self.center_y, 'type': trait}

        # A. 攻撃側
        if progress < t['switch_start']:
            # 登場
            if progress < self.t_enter:
                ratio = progress / self.t_enter
                atk['y'] = (self.center_y + self.bottom_offset) - (self.bottom_offset * ratio)
                atk['x'] = self.left_pos_x
            else:
                atk['x'] = self.left_pos_x
        else:
            # 退場
            if progress < t['switch_end']:
                ratio = (progress - t['switch_start']) / (t['switch_end'] - t['switch_start'])
                atk['x'] = self.left_pos_x - (self.left_pos_x + self.offscreen_offset) * ratio
            else:
                atk['x'] = -self.offscreen_offset * 2

        # B. 防御側
        if progress < t['switch_start']:
            pass # 画面外
        elif progress < t['switch_end']:
            # 登場 (スライドイン)
            ratio = (progress - t['switch_start']) / (t['switch_end'] - t['switch_start'])
            start_x = self.sw + self.offscreen_offset
            defn['x'] = start_x - (start_x - self.right_pos_x) * ratio
        else:
            defn['x'] = self.right_pos_x

        # C. 弾丸
        if progress >= t['fire']:
            bul['visible'] = True
            screen_center_x = self.sw // 2
            
            if progress < t['switch_start']:
                # 発射
                ratio = (progress - t['fire']) / (t['switch_start'] - t['fire'])
                start_x = self.left_pos_x + 80
                bul['x'] = start_x + (screen_center_x - start_x) * ratio
                
            elif progress < t['switch_end']:
                # 追従
                ratio = (progress - t['switch_start']) / (t['switch_end'] - t['switch_start'])
                bul['x'] = screen_center_x + (50 * ratio)
                
            else:
                # 着弾
                ratio = (progress - t['switch_end']) / (t['impact'] - t['switch_end'])
                prev_x = screen_center_x + 50
                target_hit_x = self.right_pos_x
                
                is_hit = hit_result.get('is_hit', False) if hit_result else False
                
                if progress <= t['impact']:
                    bul['x'] = prev_x + (target_hit_x - prev_x) * ratio
                else:
                    if is_hit:
                        bul['visible'] = False
                    else:
                        miss_ratio = (progress - t['impact']) / (1.0 - t['impact'])
                        bul['x'] = target_hit_x + (self.sw - target_hit_x + 100) * miss_ratio

        return {'attacker': atk, 'defender': defn, 'bullet': bul, 'effect': {'visible': False}}

    def _calc_popup_state(self, progress, t_impact, hit_result):
        """結果ポップアップの状態計算"""
        if progress <= t_impact or not hit_result:
            return {'visible': False}
        
        anim_duration = 1.0 - t_impact
        if anim_duration <= 0: anim_duration = 0.1
        
        anim_t = (progress - t_impact) / anim_duration
        anim_t = max(0.0, min(1.0, anim_t))
        
        # ターゲットの上に表示
        x = self.right_pos_x
        y = self.center_y - 60 - (40 * anim_t)
        
        return {
            'visible': True,
            'x': x,
            'y': y,
            'result': hit_result
        }

    def _apply_mirror(self, char_state, sw):
        """左右反転処理"""
        char_state['attacker']['x'] = sw - char_state['attacker']['x']
        char_state['defender']['x'] = sw - char_state['defender']['x']
        if char_state['bullet']['visible']:
            char_state['bullet']['x'] = sw - char_state['bullet']['x']


class CutinRenderer(BaseRenderer):
    """
    カットイン演出の描画を担当するクラス。
    Cinematicsが計算したStateを受け取り、Pygameで描画する。
    """

    def __init__(self, screen):
        super().__init__(screen)
        self.cinematics = CutinCinematics()

    def draw(self, attacker_visual, target_visual, progress, hit_result, mirror=False, attack_trait=None):
        """
        メイン描画メソッド。
        VisualStateを受け取り描画する（データ加工は行わない）
        """
        # 1. 状態計算（ロジック）
        state = self.cinematics.calculate_frame_state(progress, attack_trait, mirror, hit_result)
        
        # 2. 描画実行（レンダリング）
        self._render_scene(state, attacker_visual, target_visual, mirror)

    def _render_scene(self, state, attacker_visual, target_visual, mirror):
        sw, sh = self.cinematics.sw, self.cinematics.sh
        
        # 1. 背景オーバーレイ
        if state['bg_alpha'] > 0:
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, state['bg_alpha']))
            self.screen.blit(overlay, (0, 0))

        # 2. キャラクター描画
        # 攻撃側
        atk = state['attacker']
        if atk['visible'] and -200 < atk['x'] < sw + 200:
            self._draw_character_info(attacker_visual, atk['x'], atk['y'])

        # 防御側
        defn = state['defender']
        if defn['visible'] and -200 < defn['x'] < sw + 200:
            self._draw_character_info(target_visual, defn['x'], defn['y'])

        # 3. 弾丸描画
        bul = state['bullet']
        if bul['visible']:
            self._draw_bullet(bul, mirror)

        # 4. エフェクト描画
        eff = state['effect']
        if eff['visible']:
            # エフェクトはターゲットの位置に出す
            target_x = defn['x']
            target_y = defn['y']
            self._draw_slash_effect(target_x, target_y, eff['progress'], eff['start_time'], mirror)

        # 5. 黒帯 (Cinematic Bars)
        bh = state['bar_height']
        if bh > 0:
            pygame.draw.rect(self.screen, (0, 0, 0), (0, 0, sw, bh))
            pygame.draw.rect(self.screen, (0, 0, 0), (0, sh - bh, sw, bh))

        # 6. 結果ポップアップ
        pop = state['popup']
        if pop['visible']:
            # ポップアップ位置は防御側に追従させる（ミラー対応のため）
            popup_x = defn['x']
            self._draw_popup_result(popup_x, pop['y'], pop['result'])

    def _draw_bullet(self, bul, mirror):
        """弾丸の形状描画"""
        trait = bul['type']
        bx, by = bul['x'], bul['y']
        direction = -1 if mirror else 1
        
        if trait == TraitType.RIFLE:
            self._draw_rifle_bullet(bx, by, direction)
        elif trait == TraitType.GATLING:
            self._draw_gatling_bullet(bx, by, direction)
        else:
            self._draw_normal_bullet(bx, by, direction)

    def _draw_rifle_bullet(self, x, y, direction):
        size = 15
        tip = (x, y)
        back_x = x - (size * direction)
        p1 = (back_x, y - size // 2)
        p2 = (back_x, y + size // 2)
        
        # 軌跡
        trail_color = (200, 255, 255)
        ellipses = [(6, 22, 35), (9, 36, 55), (12, 50, 70)]
        for w, h, dist in ellipses:
            cx = x - (dist * direction)
            rect = pygame.Rect(0, 0, w, h)
            rect.center = (int(cx), int(y))
            pygame.draw.ellipse(self.screen, trail_color, rect, 2)
        
        pygame.draw.polygon(self.screen, (255, 255, 150), [tip, p1, p2])

    def _draw_gatling_bullet(self, x, y, direction):
        for i in range(5):
            offset_x = i * 25 * direction
            bx = x - offset_x
            offsets_y = [0, -6, 6, -3, 3]
            by = y + offsets_y[i]
            
            if -50 < bx < self.cinematics.sw + 50:
                g_size = 10
                g_tip = (bx, by)
                g_back_x = bx - (g_size * direction)
                
                g_p1 = (g_back_x, by - g_size // 2)
                g_p2 = (g_back_x, by + g_size // 2)
                pygame.draw.polygon(self.screen, (255, 200, 50), [g_tip, g_p1, g_p2])
                
                sq_size = 8
                sq_x = g_back_x if direction < 0 else g_back_x - sq_size
                sq_y = by - sq_size // 2
                pygame.draw.rect(self.screen, (255, 150, 0), (int(sq_x), int(sq_y), sq_size, sq_size))

    def _draw_normal_bullet(self, x, y, direction):
        pygame.draw.circle(self.screen, (255, 255, 50), (int(x), int(y)), 12)
        tail_len = 30
        tail_end_x = x - (tail_len * direction)
        pygame.draw.line(self.screen, (255, 200, 0), (int(x), int(y)), (int(tail_end_x), int(y)), 4)

    def _draw_slash_effect(self, cx, cy, progress, t_start, mirror):
        effect_time = 0.2
        local_t = (progress - t_start) / effect_time
        if local_t > 1.0: return
        
        alpha = int(255 * (1.0 - local_t))
        if alpha <= 0: return

        length = 150
        width = int(10 * (1.0 - local_t))
        direction = -1 if mirror else 1
        
        start_pos = (cx - (50 * direction), cy - 80)
        end_pos = (cx + (50 * direction), cy + 80)
        
        color = (255, 255, 200)
        pygame.draw.line(self.screen, color, start_pos, end_pos, width)
        
        if width > 4:
            pygame.draw.line(self.screen, (200, 100, 50), 
                             (start_pos[0]-10, start_pos[1]), 
                             (end_pos[0]-10, end_pos[1]), width // 2)

    def _draw_popup_result(self, x, y, hit_result):
        is_hit = hit_result.get('is_hit', False)
        is_critical = hit_result.get('is_critical', False)
        is_defense = hit_result.get('is_defense', False)
        damage = hit_result.get('damage', 0)

        lines = []
        if not is_hit:
            lines.append(("MISS!", (200, 200, 200)))
        else:
            if is_critical:
                lines.append(("CRITICAL!", (255, 50, 50)))
            elif is_defense:
                lines.append(("防御!", (100, 200, 255)))
            else:
                lines.append(("クリーンヒット!", (255, 220, 0)))

            if damage > 0:
                lines.append((f"-{damage}", (255, 255, 255)))
            else:
                lines.append(("NO DAMAGE", (200, 200, 200)))

        current_y = y
        for text, color in lines:
            self._draw_text_with_outline(text, x, current_y, color)
            current_y += 35

    def _draw_text_with_outline(self, text, x, y, color):
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            self.draw_text(text, (x + ox, y + oy), (0, 0, 0), 'large', 'center')
        self.draw_text(text, (x, y), color, 'large', 'center')

    def _draw_character_info(self, view_data, center_x, center_y):
        # 描画データ(view_data)は既に整形済み
        color = view_data['color']
        is_alive_map = view_data['is_alive_map']
        hp_bars = view_data.get('hp_bars')
        
        cx, cy = int(center_x), int(center_y)

        self.draw_robot_icon(cx, cy, color, is_alive_map, scale=1.0)
        if hp_bars:
            self.draw_hp_bars(cx, cy + 65, hp_bars)