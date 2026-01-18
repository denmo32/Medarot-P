"""カットイン演出管理システム"""

import pygame
from config import GAME_PARAMS
from battle.constants import PartType

class CutinRenderer:
    """カットイン演出の描画を担当するクラス"""

    def __init__(self, screen, renderer):
        self.screen = screen
        self.renderer = renderer # テキスト描画などの共通機能利用のため

    def draw(self, attacker_data, target_data, attacker_hp_data, target_hp_data, progress, hit_result, mirror=False, attack_trait=None):
        """
        カットインウィンドウを描画（スライド＆追従カメラ演出）
        """
        sw, sh = GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']
        
        # --- フェードイン係数計算 (0.0 -> 0.2) ---
        t_enter = 0.2
        fade_ratio = min(1.0, progress / t_enter) if t_enter > 0 else 1.0

        # 1. 背景オーバーレイ（滑らかに暗く）
        max_alpha = 150
        current_alpha = int(max_alpha * fade_ratio)
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, current_alpha))
        self.screen.blit(overlay, (0, 0))
        
        # --- 座標計算ロジック ---
        
        # ウィンドウエリア定義（座標基準点）
        w_w, w_h = 700, 200
        w_x, w_y = (sw - w_w) // 2, (sh - w_h) // 2
        center_y = w_y + 80
        
        # 左右の基準X座標（画面内定位置）
        left_pos_x = w_x + 100
        right_pos_x = w_x + w_w - 100
        
        # 画面外オフセット
        offscreen_offset = 400
        # 下方向オフセット（登場用）
        bottom_offset = 300

        # アニメーション進行度に基づく座標計算
        # Phase閾値
        t_switch_start = 0.45
        t_switch_end = 0.7
        t_impact = 0.8
        
        # デフォルト初期値
        attacker_x = left_pos_x
        attacker_y = center_y + bottom_offset
        
        defender_x = sw + offscreen_offset
        defender_y = center_y
        
        bullet_visible = False
        bullet_x = 0
        
        # A. 攻撃側 アニメーション
        if progress < t_switch_start:
            # 登場 (0.0 -> 0.2)
            if progress < t_enter:
                ratio = progress / t_enter
                # 下から上へ
                attacker_y = (center_y + bottom_offset) - (bottom_offset * ratio)
                attacker_x = left_pos_x
            else:
                attacker_y = center_y
                attacker_x = left_pos_x
        else:
            # 退場 (0.45 -> 0.7)
            attacker_y = center_y
            if progress < t_switch_end:
                ratio = (progress - t_switch_start) / (t_switch_end - t_switch_start)
                attacker_x = left_pos_x - (left_pos_x + offscreen_offset) * ratio
            else:
                attacker_x = -offscreen_offset * 2

        # B. 防御側 アニメーション
        if progress < t_switch_start:
            defender_x = sw + offscreen_offset
        elif progress < t_switch_end:
            # 登場 (0.45 -> 0.7)
            ratio = (progress - t_switch_start) / (t_switch_end - t_switch_start)
            defender_x = (sw + offscreen_offset) - ((sw + offscreen_offset) - right_pos_x) * ratio
        else:
            defender_x = right_pos_x

        # C. 弾丸 アニメーション
        t_fire = 0.25
        
        if progress >= t_fire:
            bullet_visible = True
            
            bullet_start_rel_x = 80
            screen_center_x = sw // 2
            
            if progress < t_switch_start:
                # 発射フェーズ
                ratio = (progress - t_fire) / (t_switch_start - t_fire)
                start_x = left_pos_x + bullet_start_rel_x
                bullet_x = start_x + (screen_center_x - start_x) * ratio
                
            elif progress < t_switch_end:
                # 追従フェーズ
                ratio = (progress - t_switch_start) / (t_switch_end - t_switch_start)
                bullet_x = screen_center_x + (50 * ratio)
                
            else:
                # 着弾フェーズ
                ratio = (progress - t_switch_end) / (t_impact - t_switch_end)
                prev_x = screen_center_x + 50
                target_hit_x = right_pos_x
                
                is_hit = hit_result.get('is_hit', False) if hit_result else False
                
                if progress <= t_impact:
                    bullet_x = prev_x + (target_hit_x - prev_x) * ratio
                else:
                    if is_hit:
                        bullet_visible = False
                    else:
                        miss_ratio = (progress - t_impact) / (1.0 - t_impact)
                        bullet_x = target_hit_x + (sw - target_hit_x + 100) * miss_ratio

        # --- ミラーリング ---
        if mirror:
            attacker_x = sw - attacker_x
            defender_x = sw - defender_x
            bullet_x = sw - bullet_x

        # --- 描画実行 (順序: キャラ/弾 -> 黒帯 -> ポップアップ) ---

        # 2. キャラクター & 弾丸 (黒帯の下)
        
        # 攻撃側
        if -200 < attacker_x < sw + 200:
            self._draw_character_info(attacker_data, attacker_hp_data, attacker_x, attacker_y, show_hp=False)

        # 防御側
        if -200 < defender_x < sw + 200:
            self._draw_character_info(target_data, target_hp_data, defender_x, defender_y, show_hp=True)

        # 弾丸
        if bullet_visible:
            pygame.draw.circle(self.screen, (255, 255, 50), (int(bullet_x), int(center_y)), 12)
            tail_len = 30
            direction = -1 if mirror else 1
            tail_end_x = bullet_x - (tail_len * direction)
            pygame.draw.line(self.screen, (255, 200, 0), (int(bullet_x), int(center_y)), (int(tail_end_x), int(center_y)), 4)

        # 3. 黒帯 (Cinematic Bars) - 最前面に描画し、滑らかに登場させる
        target_bar_height = sh // 8
        current_bar_height = int(target_bar_height * fade_ratio)
        
        if current_bar_height > 0:
            # 上の帯
            pygame.draw.rect(self.screen, (0, 0, 0), (0, 0, sw, current_bar_height))
            # 下の帯
            pygame.draw.rect(self.screen, (0, 0, 0), (0, sh - current_bar_height, sw, current_bar_height))

        # 4. 結果ポップアップ
        if progress > t_impact:
             self._draw_popup_result(defender_x, center_y, hit_result, progress, t_impact)

    def _draw_popup_result(self, center_x, center_y, hit_result, progress, t_impact):
        """結果テキストをターゲットの上にポップアップ表示"""
        if not hit_result: return

        anim_duration = 1.0 - t_impact
        anim_t = (progress - t_impact) / anim_duration
        anim_t = max(0.0, min(1.0, anim_t))
        
        offset_y = -40 * anim_t
        start_y = center_y - 60
        
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

        current_y = start_y + offset_y
        for text, color in lines:
            self._draw_text_with_outline(text, center_x, current_y, color)
            current_y += 35

    def _draw_text_with_outline(self, text, x, y, color):
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            self.renderer.draw_text(text, (x + ox, y + oy), (0, 0, 0), 'large', 'center')
        self.renderer.draw_text(text, (x, y), color, 'large', 'center')

    def _draw_character_info(self, char_data, hp_data, center_x, center_y, show_hp=True):
        """
        キャラクターのアイコンとHPバーを描画する。
        """
        is_alive_map = {item['key']: (item['current'] > 0) for item in hp_data}
        base_color = char_data['color']
        cx, cy = int(center_x), int(center_y)

        # ロボット型アイコン
        self.renderer.draw_robot_icon(cx, cy, base_color, is_alive_map, scale=1.0)
        
        # HPバー
        if show_hp:
            self.renderer.draw_hp_bars(cx, cy + 65, hp_data)