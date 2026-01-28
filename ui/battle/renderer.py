"""
バトルシーンの描画を統括するレンダラー
Snapshotデータを受け取り、Pygameへの描画命令を発行する。
"""

import pygame
import math
from config import COLORS, GAME_PARAMS
from ui.base.renderer import BaseRenderer
from .snapshot import BattleStateSnapshot
from .layout_utils import calculate_action_menu_layout
from battle.constants import TraitType, PartType

class BattleRenderer(BaseRenderer):
    """Field, UI, Cutinの描画を統合的に管理"""

    def render(self, snapshot: BattleStateSnapshot):
        """1フレームを描画"""
        self.clear()
        
        self.draw_field_guides()
        
        # 1. キャラクターとフィールド
        self._render_characters(snapshot)
        self._render_target_marker(snapshot)
        self._render_target_line(snapshot)
        
        # 2. UIパネル
        if snapshot.log_window.is_active:
            self._render_log_window(snapshot.log_window)
        
        if snapshot.action_menu.is_active:
            self._render_action_menu(snapshot.action_menu)
            
        if snapshot.game_over.is_active:
            self._render_game_over(snapshot.game_over)

        # 3. カットイン演出
        if snapshot.cutin.is_active:
            self._render_cutin(snapshot.cutin)

        self.present()

    # --- Field Rendering ---

    def draw_field_guides(self):
        center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
        offset = 40
        h = GAME_PARAMS['SCREEN_HEIGHT']
        for ox in [-offset, offset]:
            lx = center_x + ox
            pygame.draw.line(self.screen, COLORS['GUIDE_LINE'], (lx, 0), (lx, h), 1)

    def _render_characters(self, snapshot):
        for eid, char in snapshot.characters.items():
            # ホームマーカー
            pygame.draw.circle(self.screen, COLORS['HOME_MARKER'], (int(char.home_x), int(char.home_y + 20)), 22, 2)
            
            # アイコン
            cx, cy = int(char.icon_x), int(char.y + 20)
            if char.border_color:
                pygame.draw.circle(self.screen, char.border_color, (cx, cy), 22, 2)
            
            # ロボットアイコン(BaseRenderer機能)
            offset_y = 16 * 0.4
            self.draw_robot_icon(cx, cy - offset_y, char.team_color, char.part_status, scale=0.4)
            
            # 名前
            self.draw_text(char.name, (char.x - 20, char.y - 25), font_type='medium')

    def _render_target_marker(self, snapshot):
        if snapshot.target_marker_eid and snapshot.target_marker_eid in snapshot.characters:
            pos = snapshot.characters[snapshot.target_marker_eid]
            self.draw_text("▼", (pos.icon_x, pos.y - 6), (255, 255, 0), 'medium', 'center')

    def _render_target_line(self, snapshot):
        if not snapshot.target_line: return
        start_char, end_char, time_offset = snapshot.target_line
        
        sx, sy = start_char.icon_x, start_char.y + 20
        ex, ey = end_char.icon_x, end_char.y + 20
        
        dx, dy = ex - sx, ey - sy
        dist = math.hypot(dx, dy)
        if dist < 1: return
        angle = math.atan2(dy, dx)
        
        spacing = 30
        count = int(dist / spacing)
        move_offset = (time_offset * 100) % spacing
        
        for i in range(count):
            d = i * spacing + move_offset
            if d > dist: continue
            px = sx + math.cos(angle) * d
            py = sy + math.sin(angle) * d
            self._draw_triangle((px, py), angle, 8, (255, 255, 0))

    # --- UI Rendering ---

    def _render_log_window(self, data):
        wy = GAME_PARAMS['MESSAGE_WINDOW_Y']
        wh = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        ww = GAME_PARAMS['SCREEN_WIDTH']
        pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']

        self.draw_box((0, wy, ww, wh), GAME_PARAMS['MESSAGE_WINDOW_BG_COLOR'], GAME_PARAMS['MESSAGE_WINDOW_BORDER_COLOR'])
        
        for i, log in enumerate(data.logs):
            self.draw_text(log, (pad, wy + pad + i * 25), font_type='medium')

        if data.show_input_guidance:
            ui_cfg = GAME_PARAMS['UI']
            self.draw_text("Zキー or クリックで次に進む", (ww - ui_cfg['NEXT_MSG_X_OFFSET'] - 50, wy + wh - ui_cfg['NEXT_MSG_Y_OFFSET']), font_type='medium')

    def _render_action_menu(self, data):
        wy = GAME_PARAMS['MESSAGE_WINDOW_Y']
        wh = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']
        
        self.draw_text(f"{data.actor_name}のターン", (pad, wy + wh - GAME_PARAMS['UI']['TURN_TEXT_Y_OFFSET']), font_type='medium')
        
        layout = calculate_action_menu_layout(len(data.buttons))
        
        for i, (btn, rect) in enumerate(zip(data.buttons, layout)):
            bg = COLORS['BUTTON_BG'] if btn.enabled else COLORS['BUTTON_DISABLED_BG']
            border = (255, 255, 0) if i == data.selected_index else COLORS['BUTTON_BORDER']
            
            self.draw_box(rect, bg, border, 3 if i == data.selected_index else 2)
            self.draw_text(btn.label, (rect.x + 10, rect.y + 5), font_type='medium')

    def _render_game_over(self, data):
        overlay = pygame.Surface((GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']), pygame.SRCALPHA)
        overlay.fill(COLORS['NOTICE_BG'])
        self.screen.blit(overlay, (0, 0))

        color = COLORS['PLAYER'] if data.winner == "プレイヤー" else COLORS['ENEMY']
        mid_x, mid_y = GAME_PARAMS['SCREEN_WIDTH'] // 2, GAME_PARAMS['SCREEN_HEIGHT'] // 2
        
        self.draw_text(f"{data.winner}の勝利！", (mid_x, mid_y), color, 'notice', 'center')
        self.draw_text("ESCキーで終了", (mid_x, mid_y + GAME_PARAMS['NOTICE_Y_OFFSET']), COLORS['TEXT'], 'medium', 'center')

    # --- Cutin Rendering ---

    def _render_cutin(self, state):
        sw, sh = GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']
        
        # 背景
        if state.bg_alpha > 0:
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, state.bg_alpha))
            self.screen.blit(overlay, (0, 0))

        # キャラクター
        atk = state.attacker
        if atk.get('visible') and -200 < atk['x'] < sw + 200:
            cx, cy = int(atk['x']), int(atk['y'])
            self.draw_robot_icon(cx, cy, atk['color'], atk['is_alive_map'])
            if atk.get('hp_bars'):
                self.draw_hp_bars(cx, cy + 65, atk['hp_bars'])

        defn = state.defender
        if defn.get('visible') and -200 < defn['x'] < sw + 200:
            cx, cy = int(defn['x']), int(defn['y'])
            self.draw_robot_icon(cx, cy, defn['color'], defn['is_alive_map'])
            if defn.get('hp_bars'):
                self.draw_hp_bars(cx, cy + 65, defn['hp_bars'])

        # 弾丸
        if state.bullet.get('visible'):
            self._render_bullet(state.bullet, state.mirror)

        # エフェクト
        if state.effect.get('visible'):
            self._render_effect(state.defender['x'], state.defender['y'], state.effect, state.mirror)

        # 黒帯
        if state.bar_height > 0:
            pygame.draw.rect(self.screen, (0, 0, 0), (0, 0, sw, state.bar_height))
            pygame.draw.rect(self.screen, (0, 0, 0), (0, sh - state.bar_height, sw, state.bar_height))

        # ポップアップ
        if state.popup.get('visible'):
            self._render_popup(state.defender['x'], state.popup['y'], state.popup['result'])

    def _render_bullet(self, bul, mirror):
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
        
        # トレイル
        trail_color = (200, 255, 255)
        ellipses = [(6, 22, 35), (9, 36, 55), (12, 50, 70)]
        for w, h, dist in ellipses:
            cx = x - (dist * direction)
            rect = pygame.Rect(0, 0, w, h)
            rect.center = (int(cx), int(y))
            pygame.draw.ellipse(self.screen, trail_color, rect, 2)
        
        pygame.draw.polygon(self.screen, (255, 255, 150), [tip, p1, p2])

    def _draw_gatling_bullet(self, x, y, direction):
        # 簡易ガトリング：複数の弾
        for i in range(5):
            offset_x = i * 25 * direction
            bx = x - offset_x
            offsets_y = [0, -6, 6, -3, 3]
            by = y + offsets_y[i]
            
            if -50 < bx < GAME_PARAMS['SCREEN_WIDTH'] + 50:
                g_size = 10
                g_tip = (bx, by)
                g_back_x = bx - (g_size * direction)
                g_p1 = (g_back_x, by - g_size // 2)
                g_p2 = (g_back_x, by + g_size // 2)
                pygame.draw.polygon(self.screen, (255, 200, 50), [g_tip, g_p1, g_p2])

    def _draw_normal_bullet(self, x, y, direction):
        pygame.draw.circle(self.screen, (255, 255, 50), (int(x), int(y)), 12)
        tail_len = 30
        tail_end_x = x - (tail_len * direction)
        pygame.draw.line(self.screen, (255, 200, 0), (int(x), int(y)), (int(tail_end_x), int(y)), 4)

    def _render_effect(self, cx, cy, eff, mirror):
        progress = eff['progress']
        t_start = eff['start_time']
        
        effect_time = 0.2
        local_t = (progress - t_start) / effect_time
        if local_t > 1.0 or local_t < 0: return
        
        alpha = int(255 * (1.0 - local_t))
        if alpha <= 0: return

        width = int(10 * (1.0 - local_t))
        direction = -1 if mirror else 1
        start_pos = (cx - (50 * direction), cy - 80)
        end_pos = (cx + (50 * direction), cy + 80)
        
        pygame.draw.line(self.screen, (255, 255, 200), start_pos, end_pos, width)
        if width > 4:
            pygame.draw.line(self.screen, (200, 100, 50), 
                             (start_pos[0]-10, start_pos[1]), 
                             (end_pos[0]-10, end_pos[1]), width // 2)

    def _render_popup(self, x, y, hit_result):
        is_hit = hit_result.is_hit
        is_critical = hit_result.is_critical
        is_defense = hit_result.is_defense
        damage = hit_result.damage

        lines = []
        if not is_hit:
            lines.append(("MISS!", (200, 200, 200)))
        else:
            if is_critical: lines.append(("CRITICAL!", (255, 50, 50)))
            elif is_defense: lines.append(("防御!", (100, 200, 255)))
            else: lines.append(("クリーンヒット!", (255, 220, 0)))

            if damage > 0: lines.append((f"-{damage}", (255, 255, 255)))
            else: lines.append(("NO DAMAGE", (200, 200, 200)))

        current_y = y
        for text, color in lines:
            self._draw_text_with_outline(text, x, current_y, color)
            current_y += 35

    def _draw_text_with_outline(self, text, x, y, color):
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            self.draw_text(text, (x + ox, y + oy), (0, 0, 0), 'large', 'center')
        self.draw_text(text, (x, y), color, 'large', 'center')