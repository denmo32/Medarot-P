import pygame
from config import GAME_PARAMS

class CutinRenderer:
    """カットイン演出の描画を担当するクラス"""

    def __init__(self, screen, renderer):
        self.screen = screen
        self.renderer = renderer # テキスト描画などの共通機能利用のため

    def draw(self, attacker_data, target_data, progress, is_hit, mirror=False):
        """
        カットインウィンドウを描画（枠線なし、アニメーション分岐）
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

        # 攻撃側
        self._draw_character_info(attacker_data, attacker_x, attacker_y)

        # 防御側
        self._draw_character_info(target_data, target_x, target_y)

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
            
            # mirror考慮: 
            # mirror=False (左->右): current_x > target_x - 50 (ターゲットの少し左を超えたら)
            # mirror=True  (右->左): current_x < target_x + 50 (ターゲットの少し右を超えたら)
            
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
                    target_x, 
                    target_y
                )

    def _draw_character_info(self, char_data, center_x, center_y):
        # アイコン
        pygame.draw.circle(self.screen, char_data['color'], (center_x, center_y), 50)
        # 名前（アイコンの下）
        self.renderer.draw_text(char_data['name'], (center_x, center_y + 60), font_type='medium', align='center')

    def _draw_projectile_animation(self, start_x, hit_x, obj_y, miss_x, progress, is_hit):
        
        # 進行度(0.0~1.0) に基づく現在位置
        if is_hit:
            # ヒット時: start_x から hit_x まで移動して止まる
            current_x = start_x + (hit_x - start_x) * progress
            
            # 着弾エフェクト（進行度が1.0に近い場合）
            if progress > 0.95:
                # 簡易爆発（円を広げる）
                scale = (progress - 0.95) * 20 * 50
                pygame.draw.circle(self.screen, (255, 200, 50), (int(hit_x), int(obj_y)), int(10 + scale))
        else:
            # 回避時: start_x から miss_x まで突き抜ける
            current_x = start_x + (miss_x - start_x) * progress

        # 弾
        if progress < 1.0 or not is_hit:
            # 軌跡
            pygame.draw.line(self.screen, (255, 255, 0), (int(start_x), int(obj_y)), (int(current_x), int(obj_y)), 4)
            # 本体
            pygame.draw.circle(self.screen, (255, 255, 0), (int(current_x), int(obj_y)), 10)
