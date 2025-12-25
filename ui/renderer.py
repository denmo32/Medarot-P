"""描画処理を担当するプレゼンテーション層"""

import pygame
from config import COLORS, FONT_NAMES, GAME_PARAMS

class Renderer:
    """画面描画を担当するプレゼンテーションクラス"""

    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont(FONT_NAMES, 24)
        self.title_font = pygame.font.SysFont(FONT_NAMES, 32)
        self.notice_font = pygame.font.SysFont(FONT_NAMES, 36)
        self.icon_size = 32
        self.icon_radius = self.icon_size // 2

    def clear_screen(self) -> None:
        """画面を背景色でクリア"""
        self.screen.fill(COLORS['BACKGROUND'])

    def render_battle_system(self, battle_system) -> None:
        """バトルシステムの状態を描画"""
        world = battle_system.world
        
        # コンテキストの取得
        contexts = world.get_entities_with_components('battlecontext')
        if not contexts: return
        context = contexts[0][1]['battlecontext']

        # チーム名の表示
        self._render_team_titles()
        
        # 各エンティティの描画
        # RenderComponent, PositionComponent, GaugeComponent, PartHealthComponent を持つものを対象とする
        # ここでは簡易的に全エンティティスキャン（最適化余地あり）
        for eid, comps in world.entities.items():
            if 'render' in comps and 'position' in comps and 'gauge' in comps and 'parthealth' in comps and 'team' in comps:
                self._render_entity(eid, comps)

        # メッセージウィンドウの表示（画面下部）
        self._render_message_window(world, context)
        
        # ゲームオーバー表示
        self._render_game_over(context)

    def _render_entity(self, eid, comps) -> None:
        """個別のエンティティ描画"""
        hp = comps['parthealth']
        if hp.is_defeated: return

        pos = comps['position']
        gauge = comps['gauge']
        team = comps['team']
        name = comps['name']
        render = comps['render']

        # ゲージと名前の描画
        self._render_character_gauge_with_name(
            pos.x, pos.y, render.gauge_width, render.gauge_height,
            name.name, gauge.status, gauge.progress,
            team.team_type, team.team_color
        )
        # HPバー描画
        self._render_character_hp_bar(pos.x, pos.y, hp)

    def _render_team_titles(self) -> None:
        """チーム名を描画"""
        player_title = self.title_font.render("プレイヤーチーム", True, COLORS['PLAYER'])
        enemy_title = self.title_font.render("エネミーチーム", True, COLORS['ENEMY'])
        self.screen.blit(player_title, (50, 50))
        self.screen.blit(enemy_title, (450, 50))

    def _calculate_icon_position(self, start_x, gauge_status, gauge_progress, team_type) -> float:
        """アイコンの位置を計算"""
        center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
        executing_offset = 40

        if team_type == "player":
            if gauge_status == "charging":
                return start_x + (gauge_progress / 100.0) * (center_x - executing_offset - start_x)
            elif gauge_status == "executing":
                return center_x - executing_offset
            elif gauge_status == "cooldown":
                return (center_x - executing_offset) - (gauge_progress / 100.0) * ((center_x - executing_offset) - start_x)
            else:
                return start_x
        elif team_type == "enemy":
            end_x = start_x + GAME_PARAMS['GAUGE_WIDTH']
            if gauge_status == "charging":
                return end_x - (gauge_progress / 100.0) * (end_x - (center_x + executing_offset))
            elif gauge_status == "executing":
                return center_x + executing_offset
            elif gauge_status == "cooldown":
                return (center_x + executing_offset) + (gauge_progress / 100.0) * (end_x - (center_x + executing_offset))
            else:
                return end_x
        return start_x

    def _render_character_gauge_with_name(self, x, y, width, height, name, gauge_status, gauge_progress, team_type, team_color) -> None:
        """キャラクターのアイコンを描画"""
        icon_x = self._calculate_icon_position(x, gauge_status, gauge_progress, team_type)
        icon_y = y + height // 2
        pygame.draw.circle(self.screen, team_color, (int(icon_x), int(icon_y)), self.icon_radius)
        
        # 名前表示（簡易）
        name_text = self.font.render(name, True, COLORS['TEXT'])
        self.screen.blit(name_text, (x, y - 25))

    def _render_character_hp_bar(self, x, y, hp_comp) -> None:
        """キャラクターのHPバーを描画（パーツ別）"""
        part_names = ['head', 'right_arm', 'left_arm', 'leg']
        part_colors = [
            COLORS['HP_HEAD'], COLORS['HP_RIGHT_ARM'],
            COLORS['HP_LEFT_ARM'], COLORS['HP_LEG']
        ]
        
        gauge_y = y  # ゲージのY座標を基準にする
        
        for i, (part, color) in enumerate(zip(part_names, part_colors)):
            hp_bar_x = x + i * (GAME_PARAMS['HP_BAR_WIDTH'] + 5)
            hp_bar_y = gauge_y + GAME_PARAMS['HP_BAR_Y_OFFSET']
            hp_bar_width = GAME_PARAMS['HP_BAR_WIDTH']
            hp_bar_height = GAME_PARAMS['HP_BAR_HEIGHT']

            # 現在値と最大値の取得
            current = getattr(hp_comp, f"{part}_hp")
            max_val = getattr(hp_comp, f"max_{part}_hp")

            # 背景
            pygame.draw.rect(self.screen, COLORS['HP_BG'], (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height))

            # 進行バー
            hp_ratio = current / max_val if max_val > 0 else 0
            fill_width = int(hp_bar_width * hp_ratio)
            pygame.draw.rect(self.screen, color, (hp_bar_x, hp_bar_y, fill_width, hp_bar_height))

            # 枠
            pygame.draw.rect(self.screen, COLORS['TEXT'], (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height), 1)

            # ラベル (H, R, L, Leg 等、スペースがないので短縮)
            label = part[0].upper() if part != "leg" else "Lg"
            if part == "right_arm": label = "RA"
            if part == "left_arm": label = "LA"
            
            label_text = self.font.render(f"{label}", True, COLORS['TEXT'])
            # self.screen.blit(label_text, (hp_bar_x, hp_bar_y + hp_bar_height + 2)) # スペース的に厳しいので省略可

    def _render_message_window(self, world, context) -> None:
        """メッセージウィンドウを描画"""
        window_x = 0
        window_y = GAME_PARAMS['MESSAGE_WINDOW_Y']
        window_width = GAME_PARAMS['SCREEN_WIDTH']
        window_height = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        padding = GAME_PARAMS['MESSAGE_WINDOW_PADDING']

        # 背景と枠
        pygame.draw.rect(self.screen, GAME_PARAMS['MESSAGE_WINDOW_BG_COLOR'], (window_x, window_y, window_width, window_height))
        pygame.draw.rect(self.screen, GAME_PARAMS['MESSAGE_WINDOW_BORDER_COLOR'], (window_x, window_y, window_width, window_height), 2)

        # ログ表示
        recent_logs = context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:]
        for i, log in enumerate(recent_logs):
            log_text = self.font.render(log, True, COLORS['TEXT'])
            self.screen.blit(log_text, (window_x + padding, window_y + padding + i * 25))

        # 行動選択UI
        if context.waiting_for_action and not context.game_over:
            eid = context.current_turn_entity_id
            if eid in world.entities:
                name = world.entities[eid]['name'].name
                hp = world.entities[eid]['parthealth']
                
                turn_text = self.font.render(f"{name}のターン", True, COLORS['TEXT'])
                self.screen.blit(turn_text, (window_x + padding, window_y + window_height - 100))

                # ボタンパラメータ
                button_y = window_y + window_height - 60
                button_width = 80
                button_height = 40
                button_padding = 10

                # ボタン描画ヘルパー
                def draw_btn(idx, label, hp_val=None):
                    bx = window_x + padding + idx * (button_width + button_padding)
                    is_enabled = hp_val is None or hp_val > 0
                    bg = COLORS['BUTTON_BG'] if is_enabled else COLORS['BUTTON_DISABLED_BG']
                    
                    pygame.draw.rect(self.screen, bg, (bx, button_y, button_width, button_height))
                    pygame.draw.rect(self.screen, COLORS['BUTTON_BORDER'], (bx, button_y, button_width, button_height), 2)
                    
                    txt = self.font.render(label, True, COLORS['TEXT'])
                    self.screen.blit(txt, (bx + 15, button_y + 10))

                draw_btn(0, "頭部", hp.head_hp)
                draw_btn(1, "右腕", hp.right_arm_hp)
                draw_btn(2, "左腕", hp.left_arm_hp)
                draw_btn(3, "スキップ")

        # クリック待ちメッセージ
        if context.waiting_for_input and not context.game_over:
            click_text = self.font.render("クリックして次に進む", True, COLORS['TEXT'])
            self.screen.blit(click_text, (window_x + window_width - 250, window_y + window_height - 30))

    def _render_game_over(self, context) -> None:
        """ゲームオーバー画面を描画"""
        if context.game_over:
            overlay = pygame.Surface((GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']), pygame.SRCALPHA)
            overlay.fill(COLORS['NOTICE_BG'])
            self.screen.blit(overlay, (0, 0))

            res_text = f"{context.winner}の勝利！"
            color = COLORS['PLAYER'] if context.winner == "プレイヤー" else COLORS['ENEMY']
            
            result_text = self.notice_font.render(res_text, True, color)
            text_rect = result_text.get_rect(center=(GAME_PARAMS['SCREEN_WIDTH']//2, GAME_PARAMS['SCREEN_HEIGHT']//2))
            self.screen.blit(result_text, text_rect)

            restart_text = self.font.render("ESCキーで終了", True, COLORS['TEXT'])
            restart_rect = restart_text.get_rect(center=(GAME_PARAMS['SCREEN_WIDTH']//2, GAME_PARAMS['SCREEN_HEIGHT']//2 + GAME_PARAMS['NOTICE_Y_OFFSET']))
            self.screen.blit(restart_text, restart_rect)

    def update_display(self) -> None:
        """画面を更新"""
        pygame.display.flip()
