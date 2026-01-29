"""
バトルシーンの描画を統括するレンダラー
Snapshotデータを受け取り、各サブレンダラーに描画を委譲する。
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

    def __init__(self, screen):
        super().__init__(screen)
        self.field = FieldRenderer(self)
        self.ui_panel = UIPanelRenderer(self)
        self.cutin = CutinRenderer(self)

    def render(self, snapshot: BattleStateSnapshot):
        """1フレームを描画"""
        self.clear()
        
        # 1. フィールド描画
        self.field.render(snapshot)
        
        # 2. UIパネル描画
        self.ui_panel.render(snapshot)

        # 3. カットイン演出
        if snapshot.cutin.is_active:
            self.cutin.render(snapshot.cutin)

        self.present()

    def draw_text_with_outline(self, text, x, y, color, font_type='large', align='center'):
        """袋文字（縁取りテキスト）を描画する共通ユーティリティ"""
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            self.draw_text(text, (x + ox, y + oy), (0, 0, 0), font_type, align)
        self.draw_text(text, (x, y), color, font_type, align)


class FieldRenderer:
    """戦闘フィールド上のオブジェクト描画を担当"""
    def __init__(self, master: BattleRenderer):
        self.m = master

    def render(self, snapshot: BattleStateSnapshot):
        self._draw_guides()
        self._render_characters(snapshot)
        self._render_target_marker(snapshot)
        self._render_target_line(snapshot)

    def _draw_guides(self):
        center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
        offset = 40
        h = GAME_PARAMS['SCREEN_HEIGHT']
        for ox in [-offset, offset]:
            lx = center_x + ox
            pygame.draw.line(self.m.screen, COLORS['GUIDE_LINE'], (lx, 0), (lx, h), 1)

    def _render_characters(self, snapshot):
        for eid, char in snapshot.characters.items():
            # ホームマーカー
            pygame.draw.circle(self.m.screen, COLORS['HOME_MARKER'], (int(char.home_x), int(char.home_y + 20)), 22, 2)
            
            # アイコン
            cx, cy = int(char.icon_x), int(char.y + 20)
            if char.border_color:
                pygame.draw.circle(self.m.screen, char.border_color, (cx, cy), 22, 2)
            
            # ロボットアイコン(BaseRenderer機能)
            offset_y = 16 * 0.4
            self.m.draw_robot_icon(cx, cy - offset_y, char.team_color, char.part_status, scale=0.4)
            
            # 名前
            self.m.draw_text(char.name, (char.x - 20, char.y - 25), font_type='medium')

    def _render_target_marker(self, snapshot):
        if snapshot.target_marker_eid and snapshot.target_marker_eid in snapshot.characters:
            pos = snapshot.characters[snapshot.target_marker_eid]
            self.m.draw_text("▼", (pos.icon_x, pos.y - 6), (255, 255, 0), 'medium', 'center')

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
        move_offset = (time_offset * 100) % spacing
        
        for i in range(int(dist / spacing)):
            d = i * spacing + move_offset
            if d > dist: continue
            px = sx + math.cos(angle) * d
            py = sy + math.sin(angle) * d
            self.m._draw_triangle((px, py), angle, 8, (255, 255, 0))


class UIPanelRenderer:
    """メッセージ、メニュー、リザルトなどのUIパネルを担当"""
    def __init__(self, master: BattleRenderer):
        self.m = master

    def render(self, snapshot: BattleStateSnapshot):
        if snapshot.log_window.is_active:
            self._render_log_window(snapshot.log_window)
        if snapshot.action_menu.is_active:
            self._render_action_menu(snapshot.action_menu)
        if snapshot.game_over.is_active:
            self._render_game_over(snapshot.game_over)

    def _render_log_window(self, data):
        wy = GAME_PARAMS['MESSAGE_WINDOW_Y']
        wh = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        ww = GAME_PARAMS['SCREEN_WIDTH']
        pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']

        self.m.draw_box((0, wy, ww, wh), GAME_PARAMS['MESSAGE_WINDOW_BG_COLOR'], GAME_PARAMS['MESSAGE_WINDOW_BORDER_COLOR'])
        
        for i, log in enumerate(data.logs):
            self.m.draw_text(log, (pad, wy + pad + i * 25), font_type='medium')

        if data.show_input_guidance:
            ui_cfg = GAME_PARAMS['UI']
            self.m.draw_text("Zキー or クリックで次に進む", (ww - ui_cfg['NEXT_MSG_X_OFFSET'] - 50, wy + wh - ui_cfg['NEXT_MSG_Y_OFFSET']), font_type='medium')

    def _render_action_menu(self, data):
        wy = GAME_PARAMS['MESSAGE_WINDOW_Y']
        wh = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']
        
        self.m.draw_text(f"{data.actor_name}のターン", (pad, wy + wh - GAME_PARAMS['UI']['TURN_TEXT_Y_OFFSET']), font_type='medium')
        
        layout = calculate_action_menu_layout(len(data.buttons))
        for i, (btn, rect) in enumerate(zip(data.buttons, layout)):
            bg = COLORS['BUTTON_BG'] if btn.enabled else COLORS['BUTTON_DISABLED_BG']
            border = (255, 255, 0) if i == data.selected_index else COLORS['BUTTON_BORDER']
            self.m.draw_box(rect, bg, border, 3 if i == data.selected_index else 2)
            self.m.draw_text(btn.label, (rect.x + 10, rect.y + 5), font_type='medium')

    def _render_game_over(self, data):
        overlay = pygame.Surface((GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']), pygame.SRCALPHA)
        overlay.fill(COLORS['NOTICE_BG'])
        self.m.screen.blit(overlay, (0, 0))

        color = COLORS['PLAYER'] if data.winner == "プレイヤー" else COLORS['ENEMY']
        mid_x, mid_y = GAME_PARAMS['SCREEN_WIDTH'] // 2, GAME_PARAMS['SCREEN_HEIGHT'] // 2
        
        self.m.draw_text(f"{data.winner}の勝利！", (mid_x, mid_y), color, 'notice', 'center')
        self.m.draw_text("ESCキーで終了", (mid_x, mid_y + GAME_PARAMS['NOTICE_Y_OFFSET']), COLORS['TEXT'], 'medium', 'center')


class CutinRenderer:
    """カットイン演出レイヤーの描画を担当"""
    def __init__(self, master: BattleRenderer):
        self.m = master

    def render(self, state):
        sw, sh = GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']
        
        # 背景
        if state.bg_alpha > 0:
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, state.bg_alpha))
            self.m.screen.blit(overlay, (0, 0))

        # キャラクター描画
        for char_data in [state.attacker, state.defender]:
            if char_data.get('visible') and -200 < char_data['x'] < sw + 200:
                cx, cy = int(char_data['x']), int(char_data['y'])
                self.m.draw_robot_icon(cx, cy, char_data['color'], char_data['is_alive_map'])
                if char_data.get('hp_bars'):
                    self.m.draw_hp_bars(cx, cy + 65, char_data['hp_bars'])

        # 弾丸 & エフェクト
        if state.bullet.get('visible'):
            self._render_bullet(state.bullet, state.mirror)
        if state.effect.get('visible'):
            self._render_effect(state.defender['x'], state.defender['y'], state.effect, state.mirror)

        # 黒帯
        if state.bar_height > 0:
            pygame.draw.rect(self.m.screen, (0, 0, 0), (0, 0, sw, state.bar_height))
            pygame.draw.rect(self.m.screen, (0, 0, 0), (0, sh - state.bar_height, sw, state.bar_height))

        # ポップアップ
        if state.popup.get('visible'):
            self._render_popup(state.defender['x'], state.popup['y'], state.popup['result'])

    def _render_bullet(self, bul, mirror):
        trait = bul['type']
        bx, by = bul['x'], bul['y']
        dir = -1 if mirror else 1
        
        if trait == TraitType.RIFLE:
            # ライフル
            back_x = bx - (15 * dir)
            pygame.draw.polygon(self.m.screen, (255, 255, 150), [(bx, by), (back_x, by - 7), (back_x, by + 7)])
            for w, h, dist in [(6, 22, 35), (9, 36, 55), (12, 50, 70)]:
                rect = pygame.Rect(0, 0, w, h)
                rect.center = (int(bx - dist * dir), int(by))
                pygame.draw.ellipse(self.m.screen, (200, 255, 255), rect, 2)
        elif trait == TraitType.GATLING:
            # ガトリング
            for i in range(5):
                nbx, nby = bx - (i * 25 * dir), by + [0, -6, 6, -3, 3][i]
                if -50 < nbx < GAME_PARAMS['SCREEN_WIDTH'] + 50:
                    pygame.draw.polygon(self.m.screen, (255, 200, 50), [(nbx, nby), (nbx - 10 * dir, nby - 5), (nbx - 10 * dir, nby + 5)])
        else:
            # 通常
            pygame.draw.circle(self.m.screen, (255, 255, 50), (int(bx), int(by)), 12)
            pygame.draw.line(self.m.screen, (255, 200, 0), (int(bx), int(by)), (int(bx - 30 * dir), int(by)), 4)

    def _render_effect(self, cx, cy, eff, mirror):
        local_t = (eff['progress'] - eff['start_time']) / 0.2
        if not (0 <= local_t <= 1.0): return
        
        width = int(10 * (1.0 - local_t))
        if width <= 0: return
        dir = -1 if mirror else 1
        start, end = (cx - 50 * dir, cy - 80), (cx + 50 * dir, cy + 80)
        
        pygame.draw.line(self.m.screen, (255, 255, 200), start, end, width)
        if width > 4:
            pygame.draw.line(self.m.screen, (200, 100, 50), (start[0]-10, start[1]), (end[0]-10, end[1]), width // 2)

    def _render_popup(self, x, y, hit_result):
        lines = []
        if not hit_result.is_hit:
            lines.append(("MISS!", (200, 200, 200)))
        else:
            if hit_result.is_critical: lines.append(("CRITICAL!", (255, 50, 50)))
            elif hit_result.is_defense: lines.append(("防御!", (100, 200, 255)))
            else: lines.append(("クリーンヒット!", (255, 220, 0)))
            lines.append((f"-{hit_result.damage}" if hit_result.damage > 0 else "NO DAMAGE", (255, 255, 255) if hit_result.damage > 0 else (200, 200, 200)))

        for i, (text, color) in enumerate(lines):
            self.m.draw_text_with_outline(text, x, y + i * 35, color)