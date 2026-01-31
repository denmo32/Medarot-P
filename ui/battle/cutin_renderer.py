"""攻撃演出（カットイン）の描画"""

import pygame
from ui.config import SCREEN_WIDTH, SCREEN_HEIGHT
from battle.constants import TraitType

class CutinRenderer:
    def __init__(self, master):
        self.m = master

    def render(self, state):
        sw, sh = SCREEN_WIDTH, SCREEN_HEIGHT
        
        # 1. 背面のフェード
        if state.bg_alpha > 0:
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, state.bg_alpha))
            self.m.screen.blit(overlay, (0, 0))

        # 2. キャラクターとHPバー
        for char_data in [state.attacker, state.defender]:
            if char_data.get('visible') and -200 < char_data['x'] < sw + 200:
                cx, cy = int(char_data['x']), int(char_data['y'])
                self.m.widgets.draw_robot_icon(cx, cy, char_data['color'], char_data['is_alive_map'])
                if char_data.get('hp_bars'):
                    self.m.widgets.draw_hp_bars(cx, cy + 65, char_data['hp_bars'])

        # 3. 弾丸・エフェクト
        if state.bullet.get('visible'):
            self._render_bullet(state.bullet, state.mirror)
        if state.effect.get('visible'):
            self._render_effect(state.defender['x'], state.defender['y'], state.effect, state.mirror)

        # 4. 演出用の上下黒帯
        if state.bar_height > 0:
            pygame.draw.rect(self.m.screen, (0, 0, 0), (0, 0, sw, state.bar_height))
            pygame.draw.rect(self.m.screen, (0, 0, 0), (0, sh - state.bar_height, sw, state.bar_height))

        # 5. ダメージ等のポップアップ
        if state.popup.get('visible'):
            self._render_popup(state.defender['x'], state.popup['y'], state.popup['result'])

    def _render_bullet(self, bul, mirror):
        trait, bx, by = bul['type'], bul['x'], bul['y']
        dir = -1 if mirror else 1
        
        if trait == TraitType.RIFLE:
            back_x = bx - (15 * dir)
            pygame.draw.polygon(self.m.screen, (255, 255, 150), [(bx, by), (back_x, by - 7), (back_x, by + 7)])
            for dist in [35, 55, 70]:
                pygame.draw.circle(self.m.screen, (200, 255, 255), (int(bx - dist * dir), int(by)), 5, 1)
        elif trait == TraitType.GATLING:
            for i in range(5):
                nbx = bx - (i * 25 * dir)
                nby = by + [0, -6, 6, -3, 3][i]
                pygame.draw.polygon(self.m.screen, (255, 200, 50), [(nbx, nby), (nbx - 10 * dir, nby - 5), (nbx - 10 * dir, nby + 5)])
        else:
            pygame.draw.circle(self.m.screen, (255, 255, 50), (int(bx), int(by)), 12)

    def _render_effect(self, cx, cy, eff, mirror):
        local_t = (eff['progress'] - eff['start_time']) / 0.2
        if not (0 <= local_t <= 1.0): return
        width = int(10 * (1.0 - local_t))
        if width <= 0: return
        dir = -1 if mirror else 1
        pygame.draw.line(self.m.screen, (255, 255, 200), (cx - 50 * dir, cy - 80), (cx + 50 * dir, cy + 80), width)

    def _render_popup(self, x, y, hit_result):
        lines = []
        if not hit_result.is_hit:
            lines.append(("MISS!", (200, 200, 200)))
        else:
            if hit_result.is_critical: lines.append(("CRITICAL!", (255, 50, 50)))
            elif hit_result.is_defense: lines.append(("防御!", (100, 200, 255)))
            else: lines.append(("HIT!", (255, 220, 0)))
            lines.append((f"-{hit_result.damage}", (255, 255, 255) if hit_result.damage > 0 else (200, 200, 200)))

        for i, (text, color) in enumerate(lines):
            self.m.draw_text_with_outline(text, x, y + i * 35, color)