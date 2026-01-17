"""カットイン演出管理システム"""

import pygame
from config import GAME_PARAMS, COLORS
from battle.constants import PartType

class CutinRenderer:
    """カットイン演出の描画を担当するクラス"""

    def __init__(self, screen, renderer):
        self.screen = screen
        self.renderer = renderer # テキスト描画などの共通機能利用のため

    def draw(self, attacker_data, target_data, attacker_hp_data, target_hp_data, progress, hit_result, mirror=False):
        """
        カットインウィンドウを描画（枠線なし、アニメーション分岐）
        hit_result: ActionEventのcalculation_result辞書
        mirror: Trueなら 右→左 へ攻撃する（エネミー攻撃時など）
        """
        sw, sh = GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']
        
        # 背景オーバーレイ（全体を暗くする）
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        # ウィンドウエリア定義（枠線は描画しないが座標計算に使用）
        w_w, w_h = 700, 200
        w_x, w_y = (sw - w_w) // 2, (sh - w_h) // 2
        
        # 左右のキャラエリア
        char_box_w = 150
        
        # 座標定義
        left_center_x = w_x + 20 + char_box_w // 2
        right_center_x = w_x + w_w - 20 - char_box_w // 2
        center_y = w_y + 80

        if not mirror:
            # プレイヤー攻撃 (左 -> 右)
            attacker_x, attacker_y = left_center_x, center_y
            target_x, target_y = right_center_x, center_y
            
            proj_start_x = w_x + 20 + char_box_w + 20
            proj_hit_x = target_x
            proj_miss_x = sw + 50
        else:
            # エネミー攻撃 (右 -> 左)
            attacker_x, attacker_y = right_center_x, center_y
            target_x, target_y = left_center_x, center_y
            
            proj_start_x = w_x + w_w - 20 - char_box_w - 20
            proj_hit_x = target_x
            proj_miss_x = -50

        # ヒット情報の展開
        is_hit = hit_result.get('is_hit', False) if hit_result else False

        # 攻撃側
        self._draw_character_info(attacker_data, attacker_hp_data, attacker_x, attacker_y)

        # 防御側
        self._draw_character_info(target_data, target_hp_data, target_x, target_y)

        # アニメーション（弾など）
        self._draw_projectile_animation(
            proj_start_x,
            proj_hit_x,
            target_y,
            proj_miss_x,
            progress,
            is_hit
        )
        
        # 回避時はターゲットアイコンを上書きして「後ろを通った」感を出す（簡易的実装）
        if not is_hit:
            start_x = proj_start_x
            current_x = start_x + (proj_miss_x - start_x) * progress
            
            should_redraw = False
            if not mirror:
                if current_x > target_x - 50:
                    should_redraw = True
            else:
                if current_x < target_x + 50:
                    should_redraw = True
                    
            if should_redraw:
                self._draw_character_info(
                    target_data, 
                    target_hp_data,
                    target_x, 
                    target_y
                )

        # 結果ポップアップの表示 (アニメーション後半から表示)
        if progress > 0.7:
             self._draw_popup_result(target_x, target_y, hit_result, progress)

    def _draw_popup_result(self, center_x, center_y, hit_result, progress):
        """結果テキストをターゲットの上にポップアップ表示"""
        if not hit_result: return

        # アニメーション係数 (0.7 -> 1.0 の間を 0.0 -> 1.0 に正規化)
        # 1.0を超えても（CUTIN_RESULTフェーズ）1.0でクランプ
        anim_t = (progress - 0.7) / 0.3
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
            # アウトライン（影）付きで描画して視認性を上げる
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
        
        # HPデータから各パーツの生存確認マップを作成
        is_alive_map = {item['key']: (item['current'] > 0) for item in hp_data}
        
        base_color = char_data['color']
        cx, cy = int(center_x), int(center_y)

        # -- ロボット型アイコン描画 --
        self.renderer.draw_robot_icon(cx, cy, base_color, is_alive_map, scale=1.0)

        # -- HPバー描画 --
        self.renderer.draw_hp_bars(cx, cy + 65, hp_data)

    def _draw_projectile_animation(self, start_x, hit_x, obj_y, miss_x, progress, is_hit):
        
        # 進行度(0.0~1.0) に基づく現在位置
        if is_hit:
            # ヒット時: start_x から hit_x まで移動して止まる
            current_x = start_x + (hit_x - start_x) * progress
            
            # 着弾エフェクトは削除（大きすぎるため）
        else:
            # 回避時: start_x から miss_x まで突き抜ける
            current_x = start_x + (miss_x - start_x) * progress

        # 弾
        if progress < 1.0 or not is_hit:
            # 軌跡
            pygame.draw.line(self.screen, (255, 255, 0), (int(start_x), int(obj_y)), (int(current_x), int(obj_y)), 4)
            # 本体
            pygame.draw.circle(self.screen, (255, 255, 0), (int(current_x), int(obj_y)), 10)