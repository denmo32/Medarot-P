"""カットイン演出管理システム"""

import pygame
from config import GAME_PARAMS, COLORS
from battle.constants import PartType

class CutinRenderer:
    """カットイン演出の描画を担当するクラス"""

    def __init__(self, screen, renderer):
        self.screen = screen
        self.renderer = renderer # テキスト描画などの共通機能利用のため

    def draw(self, attacker_data, target_data, attacker_hp_data, target_hp_data, progress, is_hit, mirror=False):
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
                    target_hp_data,
                    target_x, 
                    target_y
                )

    def _draw_character_info(self, char_data, hp_data, center_x, center_y):
        """
        キャラクターのアイコンとHPバーを描画する。
        アイコンは各パーツ（頭・腕・脚）の集合体として描画し、破壊されたパーツはグレーにする。
        """
        
        # HPデータから各パーツの生存確認マップを作成
        is_alive_map = {item['key']: (item['current'] > 0) for item in hp_data}
        
        base_color = char_data['color']
        broken_color = (60, 60, 60) # 破壊時はダークグレー

        def get_col(part_key):
            return base_color if is_alive_map.get(part_key, False) else broken_color

        cx, cy = int(center_x), int(center_y)

        # -- ロボット型アイコン描画 (幾何学図形で描く) --
        
        # 1. サイズ・形状定義
        # 腕・脚の矩形
        limb_w, limb_h = 16, 48
        
        # 胸部（逆三角形）
        chest_a = 40
        chest_h = 40
        
        # 頭部（円）
        # 胸部に合わせてバランス良く（直径32程度）
        head_r = 16

        # 2. 配置基準 Y座標 (shoulder_y: 胸部の上辺、腕の上端、頭部の下端)
        # cy を中心付近として、少し上にオフセット
        shoulder_y = cy - 16

        # 3. 各パーツ座標計算

        # 頭部 (Head): 円
        # 中心Y = shoulder_y - head_r (上辺に接する)
        head_cy = shoulder_y - head_r

        # 胸部 (Chest): 逆正三角形
        # 頂点: 左上, 右上, 下
        # Headの一部として扱う
        chest_points = [
            (cx - chest_a // 2, shoulder_y),
            (cx + chest_a // 2, shoulder_y),
            (cx, shoulder_y + chest_h)
        ]

        # 脚部 (Legs): 矩形 x 2
        # 胸部の下の方から配置。少し隙間を空けて二脚感。
        # 上端Y: 胸部下頂点より少し上にして接続感を出す
        legs_y = shoulder_y + chest_h - 8
        leg_gap = 4
        # 左脚: 中心より左
        l_leg_x = cx - leg_gap - limb_w
        # 右脚: 中心より右
        r_leg_x = cx + leg_gap

        # 腕部 (Arms): 矩形 x 2
        # 胸部の左右に配置。
        arm_gap = 4
        arms_y = shoulder_y
        # 左腕: 胸の左端より外側
        l_arm_x = cx - (chest_a // 2) - arm_gap - limb_w
        # 右腕: 胸の右端より外側
        r_arm_x = cx + (chest_a // 2) + arm_gap


        # 4. 描画実行 (奥から手前へ)
        
        # 脚部 (Legs)
        pygame.draw.rect(self.screen, get_col(PartType.LEGS), (l_leg_x, legs_y, limb_w, limb_h))
        pygame.draw.rect(self.screen, get_col(PartType.LEGS), (r_leg_x, legs_y, limb_w, limb_h))

        # 腕部 (Arms)
        pygame.draw.rect(self.screen, get_col(PartType.LEFT_ARM), (l_arm_x, arms_y, limb_w, limb_h))
        pygame.draw.rect(self.screen, get_col(PartType.RIGHT_ARM), (r_arm_x, arms_y, limb_w, limb_h))

        # 胸部 (Chest -> Head color)
        pygame.draw.polygon(self.screen, get_col(PartType.HEAD), chest_points)
        
        # 頭部 (Head -> Head color)
        pygame.draw.circle(self.screen, get_col(PartType.HEAD), (cx, head_cy), head_r)

        # -- HPバー描画 --
        # Renderer.draw_hp_bars を利用する。
        # アイコン下端: legs_y + limb_h = (cy - 20 + 36 - 8) + 45 = cy + 53
        # 少し余裕を持って配置
        self.renderer.draw_hp_bars(cx, cy + 65, hp_data)

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