"""カットイン演出管理システム"""

import pygame
import math
from config import GAME_PARAMS
from battle.constants import PartType, TraitType

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
        bottom_offset = 400
        # 上方向オフセット（防御側登場用）
        top_offset = 400

        # 初期値
        attacker_x = -1000
        attacker_y = center_y
        defender_x = sw + 1000
        defender_y = center_y
        
        bullet_visible = False
        bullet_x = 0
        slash_visible = False
        
        # 格闘攻撃判定
        is_melee = (attack_trait in TraitType.MELEE_TRAITS)

        # 結果表示タイミング（デフォルト）
        t_impact = 0.8

        if is_melee:
            # === 格闘アクション (接近 -> 攻撃 -> 離脱) ===
            t_dash_start = 0.35
            t_hit = 0.55
            t_leave_start = 0.75
            t_impact = t_hit # ポップアップ表示タイミングを合わせる

            # A. 攻撃側 アニメーション
            if progress < t_enter:
                # 登場 (下から)
                ratio = progress / t_enter
                attacker_y = (center_y + bottom_offset) - (bottom_offset * ratio)
                attacker_x = left_pos_x
            elif progress < t_dash_start:
                # 溜め (定位置)
                attacker_y = center_y
                attacker_x = left_pos_x
            elif progress < t_hit:
                # 急接近 (定位置 -> 敵の目前)
                ratio = (progress - t_dash_start) / (t_hit - t_dash_start)
                # イージング (加速)
                ratio = ratio * ratio
                attacker_y = center_y
                # 敵の手前(right_pos_x - 100)まで移動
                target_x = right_pos_x - 100
                attacker_x = left_pos_x + (target_x - left_pos_x) * ratio
            elif progress < t_leave_start:
                # 攻撃ヒット中 (位置固定)
                attacker_y = center_y
                attacker_x = right_pos_x - 100
                slash_visible = True
            else:
                # 離脱 (相手の後ろを通り抜ける)
                ratio = (progress - t_leave_start) / (1.0 - t_leave_start)
                # イージング（加速）
                ratio = ratio * ratio
                
                start_x = right_pos_x - 100
                target_x = sw + offscreen_offset # 画面右外へ
                
                attacker_x = start_x + (target_x - start_x) * ratio
                attacker_y = center_y

            # B. 防御側 アニメーション
            if progress < t_enter:
                # 登場 (上から) - 攻撃側と同時
                ratio = progress / t_enter
                defender_y = (center_y - top_offset) + (top_offset * ratio)
                defender_x = right_pos_x
            else:
                defender_y = center_y
                defender_x = right_pos_x

        else:
            # === 射撃アクション (弾発射) ===
            t_switch_start = 0.45
            t_switch_end = 0.7
            t_impact = 0.8

            # A. 攻撃側 アニメーション
            if progress < t_switch_start:
                # 登場 (0.0 -> 0.2)
                if progress < t_enter:
                    ratio = progress / t_enter
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
                # まだ画面外
                defender_x = sw + offscreen_offset
            elif progress < t_switch_end:
                # 登場 (0.45 -> 0.7) - 射撃は横からスライドイン
                ratio = (progress - t_switch_start) / (t_switch_end - t_switch_start)
                defender_x = (sw + offscreen_offset) - ((sw + offscreen_offset) - right_pos_x) * ratio
                defender_y = center_y
            else:
                defender_x = right_pos_x
                defender_y = center_y

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

        # 2. キャラクター & 弾丸/エフェクト (黒帯の下)
        
        # 攻撃側
        if -200 < attacker_x < sw + 200:
            self._draw_character_info(attacker_data, attacker_hp_data, attacker_x, attacker_y, show_hp=False)

        # 防御側
        if -200 < defender_x < sw + 200:
            self._draw_character_info(target_data, target_hp_data, defender_x, defender_y, show_hp=True)

        # 弾丸
        if bullet_visible:
            direction = -1 if mirror else 1
            
            if attack_trait == TraitType.RIFLE:
                # ライフル: 三角形の弾 + 縦長ドーナツ型楕円の軌跡 (大・中・小)
                size = 15
                tip = (bullet_x, center_y)
                back_x = bullet_x - (size * direction)
                
                # 三角形の頂点
                p1 = (back_x, center_y - size // 2)
                p2 = (back_x, center_y + size // 2)
                
                # 軌跡 (小・中・大の楕円)
                trail_color = (200, 255, 255)
                # (幅, 高さ, 弾からの距離)
                ellipses = [
                    (6, 22, 35),  # 小
                    (9, 36, 55),  # 中
                    (12, 50, 70)  # 大
                ]
                
                for w, h, dist in ellipses:
                    cx = bullet_x - (dist * direction)
                    rect = pygame.Rect(0, 0, w, h)
                    rect.center = (int(cx), int(center_y))
                    # ドーナツ型 (線幅指定)
                    pygame.draw.ellipse(self.screen, trail_color, rect, 2)
                
                # 本体描画
                pygame.draw.polygon(self.screen, (255, 255, 150), [tip, p1, p2])

            elif attack_trait == TraitType.GATLING:
                # ガトリング: 5つの小さめの弾 (四角+三角 □▷)
                for i in range(5):
                    # 少しずつ後ろにずらす
                    offset_x = i * 25 * direction
                    bx = bullet_x - offset_x
                    
                    # Y軸も少しバラつかせる (固定パターン)
                    offsets_y = [0, -6, 6, -3, 3]
                    by = center_y + offsets_y[i]
                    
                    # 画面内にある場合のみ描画
                    if -50 < bx < sw + 50:
                        g_size = 10
                        g_tip = (bx, by)
                        g_back_x = bx - (g_size * direction)
                        
                        # 三角形部分 (先端)
                        g_p1 = (g_back_x, by - g_size // 2)
                        g_p2 = (g_back_x, by + g_size // 2)
                        pygame.draw.polygon(self.screen, (255, 200, 50), [g_tip, g_p1, g_p2])
                        
                        # 四角形部分 (後ろ)
                        sq_size = 8
                        sq_x = g_back_x if direction < 0 else g_back_x - sq_size
                        sq_y = by - sq_size // 2
                        pygame.draw.rect(self.screen, (255, 150, 0), (int(sq_x), int(sq_y), sq_size, sq_size))

            else:
                # 通常弾 (その他)
                pygame.draw.circle(self.screen, (255, 255, 50), (int(bullet_x), int(center_y)), 12)
                tail_len = 30
                tail_end_x = bullet_x - (tail_len * direction)
                pygame.draw.line(self.screen, (255, 200, 0), (int(bullet_x), int(center_y)), (int(tail_end_x), int(center_y)), 4)
            
        # スラッシュエフェクト（格闘用）
        if slash_visible:
            self._draw_slash_effect(defender_x, center_y, progress, mirror)

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

    def _draw_slash_effect(self, cx, cy, progress, mirror):
        """格闘攻撃の軌跡（スラッシュ）を描画"""
        # アニメーション係数 (短時間で消える)
        # 表示開始から0.2秒程度で消える
        effect_time = 0.2
        # progressは t_hit (0.55) から t_leave_start (0.75) の間
        t_start = 0.55
        
        local_t = (progress - t_start) / effect_time
        if local_t > 1.0: return
        
        alpha = int(255 * (1.0 - local_t))
        if alpha <= 0: return

        # エフェクトの形状 (斜め線)
        length = 150
        width = int(10 * (1.0 - local_t))
        
        # ミラー時は反転
        direction = -1 if mirror else 1
        
        # 振り下ろし: 左上 -> 右下 (mirror: 右上 -> 左下)
        start_pos = (cx - (50 * direction), cy - 80)
        end_pos = (cx + (50 * direction), cy + 80)
        
        # Pygameでアルファ値付きラインを描くにはSurfaceが必要
        # ここでは簡易的に加算合成的な色で描画
        color = (255, 255, 200) # 白っぽい黄色
        
        pygame.draw.line(self.screen, color, start_pos, end_pos, width)
        
        # 残像（少しずらす）
        if width > 4:
            pygame.draw.line(self.screen, (200, 100, 50), 
                             (start_pos[0]-10, start_pos[1]), 
                             (end_pos[0]-10, end_pos[1]), width // 2)

    def _draw_popup_result(self, center_x, center_y, hit_result, progress, t_impact):
        """結果テキストをターゲットの上にポップアップ表示"""
        if not hit_result: return

        anim_duration = 1.0 - t_impact
        # 0除算対策
        if anim_duration <= 0: anim_duration = 0.1
            
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