"""カットイン演出の描画コンポーネント"""

import pygame
from config import GAME_PARAMS
from battle.constants import TraitType
from .base_renderer import BaseRenderer

class CutinRenderer(BaseRenderer):
    """
    カットイン演出の描画を担当するクラス。
    ViewModelが計算した描画指示（State）を受け取り、Pygameで画面に転記する。
    """

    def __init__(self, screen):
        super().__init__(screen)

    def draw(self, state):
        """
        メイン描画メソッド。
        ViewModelによってピクセル座標計算が済んでいる前提で、レイヤー順に描画する。
        """
        if not state: return
        
        sw, sh = GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']
        mirror = state['mirror']
        
        # 1. 背景オーバーレイ
        if state['bg_alpha'] > 0:
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, state['bg_alpha']))
            self.screen.blit(overlay, (0, 0))

        # 2. キャラクター描画
        # 攻撃側
        atk = state['attacker']
        if atk['visible'] and -200 < atk['x'] < sw + 200:
            self._draw_character_info(atk, atk['x'], atk['y'])

        # 防御側
        defn = state['defender']
        if defn['visible'] and -200 < defn['x'] < sw + 200:
            self._draw_character_info(defn, defn['x'], defn['y'])

        # 3. 弾丸描画
        bul = state['bullet']
        if bul['visible']:
            self._draw_bullet(bul, mirror)

        # 4. エフェクト描画
        eff = state['effect']
        if eff['visible']:
            # エフェクトはターゲットの位置に出す
            self._draw_slash_effect(defn['x'], defn['y'], eff['progress'], eff['start_time'], mirror)

        # 5. 黒帯 (Cinematic Bars)
        bh = state['bar_height']
        if bh > 0:
            pygame.draw.rect(self.screen, (0, 0, 0), (0, 0, sw, bh))
            pygame.draw.rect(self.screen, (0, 0, 0), (0, sh - bh, sw, bh))

        # 6. 結果ポップアップ
        pop = state['popup']
        if pop['visible']:
            # ポップアップ位置は防御側に追従
            self._draw_popup_result(defn['x'], pop['y'], pop['result'])

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
            
            if -50 < bx < GAME_PARAMS['SCREEN_WIDTH'] + 50:
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

    def _draw_popup_result(self, x, y, hit_result):
        is_hit = hit_result.is_hit if hit_result else False
        is_critical = hit_result.is_critical if hit_result else False
        is_defense = hit_result.is_defense if hit_result else False
        damage = hit_result.damage if hit_result else 0

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

    def _draw_character_info(self, visual_data, center_x, center_y):
        cx, cy = int(center_x), int(center_y)
        self.draw_robot_icon(cx, cy, visual_data['color'], visual_data['is_alive_map'], scale=1.0)
        if visual_data.get('hp_bars'):
            self.draw_hp_bars(cx, cy + 65, visual_data['hp_bars'])