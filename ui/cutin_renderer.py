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
        
        演出フロー:
        0.0 - 0.2: 攻撃側スライドイン (画面外 -> 定位置)
        0.2 - 0.45: 攻撃側静止、発射 (攻撃側 -> 中央方向へ)
        0.45 - 0.7: カメラ追従 & 入れ替わり (攻撃側フレームアウト、防御側フレームイン)
        0.7 - 1.0: 着弾 & 結果表示
        """
        sw, sh = GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']
        
        # 背景オーバーレイ（全体を暗くする）
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        # ウィンドウエリア定義（座標基準点）
        w_w, w_h = 700, 200
        w_x, w_y = (sw - w_w) // 2, (sh - w_h) // 2
        center_y = w_y + 80
        
        # 左右の基準X座標（画面内定位置）
        left_pos_x = w_x + 100
        right_pos_x = w_x + w_w - 100
        
        # 画面外オフセット
        offscreen_offset = 400

        # --- アニメーション進行度に基づく座標計算 ---
        # 基本は Left(Attacker) -> Right(Defender) の動きで計算し、Mirrorなら反転する

        # Phase閾値
        t_enter = 0.2
        t_switch_start = 0.45
        t_switch_end = 0.7
        t_impact = 0.8
        
        # デフォルトは画面外
        attacker_x = -offscreen_offset
        defender_x = sw + offscreen_offset
        bullet_visible = False
        bullet_x = 0
        
        # 1. 攻撃側 アニメーション
        if progress < t_switch_start:
            # 登場 (0.0 -> 0.2)
            if progress < t_enter:
                ratio = progress / t_enter
                attacker_x = -offscreen_offset + (left_pos_x - (-offscreen_offset)) * ratio
            else:
                attacker_x = left_pos_x
        else:
            # 退場 (0.45 -> 0.7)
            if progress < t_switch_end:
                ratio = (progress - t_switch_start) / (t_switch_end - t_switch_start)
                attacker_x = left_pos_x - (left_pos_x + offscreen_offset) * ratio
            else:
                attacker_x = -offscreen_offset * 2 # 完全に見えない位置

        # 2. 防御側 アニメーション
        if progress < t_switch_start:
            defender_x = sw + offscreen_offset # まだ来ない
        elif progress < t_switch_end:
            # 登場 (0.45 -> 0.7)
            ratio = (progress - t_switch_start) / (t_switch_end - t_switch_start)
            defender_x = (sw + offscreen_offset) - ((sw + offscreen_offset) - right_pos_x) * ratio
        else:
            defender_x = right_pos_x

        # 3. 弾丸 アニメーション
        # 発射タイミング 0.25あたりから
        t_fire = 0.25
        
        if progress >= t_fire:
            bullet_visible = True
            # 弾の移動計算 (カメラワーク含む相対的な見た目位置)
            # 0.25 -> 0.45 : Attackerの前から画面中央へ
            # 0.45 -> 0.70 : 画面中央付近をキープ（カメラが追従しているため）
            # 0.70 -> 0.80 : 中央からDefenderへ
            
            bullet_start_x = attacker_x + 80 # 少し前
            screen_center_x = sw // 2
            
            if progress < t_switch_start:
                # 発射フェーズ
                ratio = (progress - t_fire) / (t_switch_start - t_fire)
                bullet_x = left_pos_x + 80 + (screen_center_x - (left_pos_x + 80)) * ratio
            elif progress < t_switch_end:
                # 追従フェーズ（中央を少し進む）
                ratio = (progress - t_switch_start) / (t_switch_end - t_switch_start)
                # 中央から少し右へ
                bullet_x = screen_center_x + (50 * ratio)
            else:
                # 着弾フェーズ
                # 0.7 -> 0.8 (Impact) -> 1.0 (Through if miss)
                ratio = (progress - t_switch_end) / (t_impact - t_switch_end)
                # 直前の位置からターゲットへ
                prev_x = screen_center_x + 50
                target_hit_x = right_pos_x
                
                # 命中判定により挙動変化
                is_hit = hit_result.get('is_hit', False) if hit_result else False
                
                if progress <= t_impact:
                    bullet_x = prev_x + (target_hit_x - prev_x) * ratio
                else:
                    if is_hit:
                        bullet_visible = False # 着弾消滅
                    else:
                        # Miss: 突き抜ける
                        miss_ratio = (progress - t_impact) / (1.0 - t_impact)
                        bullet_x = target_hit_x + (sw - target_hit_x + 100) * miss_ratio

        # --- ミラーリング（敵攻撃時の反転） ---
        if mirror:
            # 画面中央を中心にX座標を反転
            attacker_x = sw - attacker_x
            defender_x = sw - defender_x
            bullet_x = sw - bullet_x

        # --- 描画実行 ---

        # 攻撃側
        if -200 < attacker_x < sw + 200:
            self._draw_character_info(attacker_data, attacker_hp_data, attacker_x, center_y)

        # 防御側
        if -200 < defender_x < sw + 200:
            self._draw_character_info(target_data, target_hp_data, defender_x, center_y)

        # 弾丸
        if bullet_visible:
            pygame.draw.circle(self.screen, (255, 255, 50), (int(bullet_x), int(center_y)), 12)
            # 簡易エフェクト（尾ひれ）
            tail_len = 30
            direction = -1 if mirror else 1
            tail_end_x = bullet_x - (tail_len * direction)
            pygame.draw.line(self.screen, (255, 200, 0), (int(bullet_x), int(center_y)), (int(tail_end_x), int(center_y)), 4)

        # 結果ポップアップ (着弾後)
        if progress > t_impact:
             # 表示位置は防御側座標
             self._draw_popup_result(defender_x, center_y, hit_result, progress, t_impact)

    def _draw_popup_result(self, center_x, center_y, hit_result, progress, t_impact):
        """結果テキストをターゲットの上にポップアップ表示"""
        if not hit_result: return

        # アニメーション係数
        anim_duration = 1.0 - t_impact
        anim_t = (progress - t_impact) / anim_duration
        anim_t = max(0.0, min(1.0, anim_t))
        
        # 下から上へ少し浮き上がる動き
        offset_y = -40 * anim_t
        start_y = center_y - 60 # キャラの頭上あたり
        
        is_hit = hit_result.get('is_hit', False)
        is_critical = hit_result.get('is_critical', False)
        is_defense = hit_result.get('is_defense', False)
        damage = hit_result.get('damage', 0)

        lines = []
        if not is_hit:
            lines.append(("MISS!", (200, 200, 200))) # 灰色
        else:
            if is_critical:
                lines.append(("CRITICAL!", (255, 50, 50))) # 赤
            elif is_defense:
                lines.append(("防御!", (100, 200, 255))) # 青
            else:
                lines.append(("クリーンヒット!", (255, 220, 0))) # 黄色

            if damage > 0:
                lines.append((f"-{damage}", (255, 255, 255)))
            else:
                lines.append(("NO DAMAGE", (200, 200, 200)))

        # テキスト描画
        current_y = start_y + offset_y
        
        for text, color in lines:
            self._draw_text_with_outline(text, center_x, current_y, color)
            current_y += 35 # 行送り

    def _draw_text_with_outline(self, text, x, y, color):
        """簡易的なアウトライン付きテキスト描画"""
        # 黒い縁取り
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            self.renderer.draw_text(text, (x + ox, y + oy), (0, 0, 0), 'large', 'center')
        
        # 本体
        self.renderer.draw_text(text, (x, y), color, 'large', 'center')

    def _draw_character_info(self, char_data, hp_data, center_x, center_y):
        """
        キャラクターのアイコンとHPバーを描画する。
        """
        is_alive_map = {item['key']: (item['current'] > 0) for item in hp_data}
        base_color = char_data['color']
        cx, cy = int(center_x), int(center_y)

        # ロボット型アイコン
        self.renderer.draw_robot_icon(cx, cy, base_color, is_alive_map, scale=1.0)
        # HPバー
        self.renderer.draw_hp_bars(cx, cy + 65, hp_data)