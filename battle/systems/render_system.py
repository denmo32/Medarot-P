"""描画システム"""

import pygame
from core.ecs import System
from config import COLORS, FONT_NAMES, GAME_PARAMS

class RenderSystem(System):
    """
    ECSアーキテクチャにおける描画担当システム。
    Worldの状態を読み取り、画面への描画を行う。
    """
    def __init__(self, world, screen):
        super().__init__(world)
        self.screen = screen
        self.font = pygame.font.SysFont(FONT_NAMES, 24)
        self.title_font = pygame.font.SysFont(FONT_NAMES, 32)
        self.notice_font = pygame.font.SysFont(FONT_NAMES, 36)
        self.icon_size = 32
        self.icon_radius = self.icon_size // 2

    def update(self, dt: float = 0.016):
        """
        描画更新処理。
        他のシステムと異なり、dtによる状態変化ではなく、現在の状態の可視化を行う。
        """
        # 1. 画面クリア
        self.screen.fill(COLORS['BACKGROUND'])

        # 2. コンテキスト取得
        contexts = self.world.get_entities_with_components('battlecontext')
        if not contexts: return
        context = contexts[0][1]['battlecontext']

        # 3. 各要素の描画
        self._render_team_titles()
        self._render_entities()
        self._render_message_window(context)
        self._render_game_over(context)

        # 4. 画面フリップ（表示更新）
        pygame.display.flip()

    def _render_entities(self):
        """全エンティティの描画"""
        for eid, comps in self.world.entities.items():
            if 'render' in comps and 'position' in comps and 'gauge' in comps and 'partlist' in comps and 'team' in comps and 'defeated' in comps:
                self._render_single_entity(eid, comps)

    def _render_single_entity(self, eid, comps):
        """個別のエンティティ描画"""
        defeated = comps['defeated']
        if defeated.is_defeated: return

        pos = comps['position']
        gauge = comps['gauge']
        team = comps['team']
        name = comps['name']
        render = comps['render']
        part_list = comps['partlist']

        # ゲージと名前
        self._render_gauge_icon(
            pos.x, pos.y, render.gauge_width, render.gauge_height,
            name.name, gauge.status, gauge.progress,
            team.team_type, team.team_color
        )
        # HPバー
        self._render_hp_bars(pos.x, pos.y, part_list)

    def _render_gauge_icon(self, x, y, width, height, name, status, progress, team_type, team_color):
        """ATBゲージのアイコンと名前を描画"""
        # アイコン位置計算
        center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
        executing_offset = 40
        icon_x = x

        if team_type == "player":
            if status == "charging":
                icon_x = x + (progress / 100.0) * (center_x - executing_offset - x)
            elif status == "executing":
                icon_x = center_x - executing_offset
            elif status == "cooldown":
                icon_x = (center_x - executing_offset) - (progress / 100.0) * ((center_x - executing_offset) - x)
        elif team_type == "enemy":
            end_x = x + GAME_PARAMS['GAUGE_WIDTH']
            if status == "charging":
                icon_x = end_x - (progress / 100.0) * (end_x - (center_x + executing_offset))
            elif status == "executing":
                icon_x = center_x + executing_offset
            elif status == "cooldown":
                icon_x = (center_x + executing_offset) + (progress / 100.0) * (end_x - (center_x + executing_offset))
            else:
                icon_x = end_x

        icon_y = y + height // 2
        
        # アイコン描画
        pygame.draw.circle(self.screen, team_color, (int(icon_x), int(icon_y)), self.icon_radius)
        
        # 名前描画
        name_text = self.font.render(name, True, COLORS['TEXT'])
        self.screen.blit(name_text, (x, y - 25))

    def _render_hp_bars(self, x, y, part_list_comp):
        """パーツ別HPバーの描画"""
        part_names = ['head', 'right_arm', 'left_arm', 'leg']
        part_colors = [COLORS['HP_HEAD'], COLORS['HP_RIGHT_ARM'], COLORS['HP_LEFT_ARM'], COLORS['HP_LEG']]

        for i, (part, color) in enumerate(zip(part_names, part_colors)):
            hp_bar_x = x + i * (GAME_PARAMS['HP_BAR_WIDTH'] + 5)
            hp_bar_y = y + GAME_PARAMS['HP_BAR_Y_OFFSET']
            w = GAME_PARAMS['HP_BAR_WIDTH']
            h = GAME_PARAMS['HP_BAR_HEIGHT']

            part_id = part_list_comp.parts.get(part)
            if part_id:
                part_comps = self.world.entities.get(part_id)
                if part_comps:
                    health = part_comps.get('health')
                    if health:
                        current = health.hp
                        max_val = health.max_hp

                        # 背景
                        pygame.draw.rect(self.screen, COLORS['HP_BG'], (hp_bar_x, hp_bar_y, w, h))
                        # 進行バー
                        if max_val > 0:
                            fill_w = int(w * (current / max_val))
                            pygame.draw.rect(self.screen, color, (hp_bar_x, hp_bar_y, fill_w, h))
                        # 枠
                        pygame.draw.rect(self.screen, COLORS['TEXT'], (hp_bar_x, hp_bar_y, w, h), 1)

    def _render_team_titles(self):
        player_title = self.title_font.render("プレイヤーチーム", True, COLORS['PLAYER'])
        enemy_title = self.title_font.render("エネミーチーム", True, COLORS['ENEMY'])
        self.screen.blit(player_title, (50, 50))
        self.screen.blit(enemy_title, (450, 50))

    def _render_message_window(self, context):
        wx = 0
        wy = GAME_PARAMS['MESSAGE_WINDOW_Y']
        ww = GAME_PARAMS['SCREEN_WIDTH']
        wh = GAME_PARAMS['MESSAGE_WINDOW_HEIGHT']
        pad = GAME_PARAMS['MESSAGE_WINDOW_PADDING']

        # ウィンドウ背景
        pygame.draw.rect(self.screen, GAME_PARAMS['MESSAGE_WINDOW_BG_COLOR'], (wx, wy, ww, wh))
        pygame.draw.rect(self.screen, GAME_PARAMS['MESSAGE_WINDOW_BORDER_COLOR'], (wx, wy, ww, wh), 2)

        # ログ表示
        recent_logs = context.battle_log[-GAME_PARAMS['LOG_DISPLAY_LINES']:]
        for i, log in enumerate(recent_logs):
            txt = self.font.render(log, True, COLORS['TEXT'])
            self.screen.blit(txt, (wx + pad, wy + pad + i * 25))

        # 行動選択UI
        if context.waiting_for_action and not context.game_over:
            self._render_action_menu(context, wx, wy, wh, pad)

        # クリック待ちメッセージ
        if context.waiting_for_input and not context.game_over:
            txt = self.font.render("クリックして次に進む", True, COLORS['TEXT'])
            self.screen.blit(txt, (wx + ww - 250, wy + wh - 30))

    def _render_action_menu(self, context, wx, wy, wh, pad):
        eid = context.current_turn_entity_id
        if eid not in self.world.entities: return

        comps = self.world.entities[eid]
        name = comps['name'].name
        part_list = comps['partlist']

        turn_text = self.font.render(f"{name}のターン", True, COLORS['TEXT'])
        self.screen.blit(turn_text, (wx + pad, wy + wh - 100))

        btn_y = wy + wh - 60
        btn_w = 80
        btn_h = 40
        btn_pad = 10

        # 各パーツのHPを取得
        head_hp = 0
        right_arm_hp = 0
        left_arm_hp = 0

        head_id = part_list.parts.get('head')
        if head_id:
            head_comps = self.world.entities.get(head_id)
            if head_comps:
                health = head_comps.get('health')
                if health:
                    head_hp = health.hp

        right_arm_id = part_list.parts.get('right_arm')
        if right_arm_id:
            right_arm_comps = self.world.entities.get(right_arm_id)
            if right_arm_comps:
                health = right_arm_comps.get('health')
                if health:
                    right_arm_hp = health.hp

        left_arm_id = part_list.parts.get('left_arm')
        if left_arm_id:
            left_arm_comps = self.world.entities.get(left_arm_id)
            if left_arm_comps:
                health = left_arm_comps.get('health')
                if health:
                    left_arm_hp = health.hp

        self._draw_button(0, "頭部", head_hp, wx, pad, btn_y, btn_w, btn_h, btn_pad)
        self._draw_button(1, "右腕", right_arm_hp, wx, pad, btn_y, btn_w, btn_h, btn_pad)
        self._draw_button(2, "左腕", left_arm_hp, wx, pad, btn_y, btn_w, btn_h, btn_pad)
        self._draw_button(3, "スキップ", 1, wx, pad, btn_y, btn_w, btn_h, btn_pad)

    def _draw_button(self, idx, label, hp_val, wx, pad, by, bw, bh, bpad):
        bx = wx + pad + idx * (bw + bpad)
        is_enabled = hp_val > 0
        bg = COLORS['BUTTON_BG'] if is_enabled else COLORS['BUTTON_DISABLED_BG']
        
        pygame.draw.rect(self.screen, bg, (bx, by, bw, bh))
        pygame.draw.rect(self.screen, COLORS['BUTTON_BORDER'], (bx, by, bw, bh), 2)
        
        txt = self.font.render(label, True, COLORS['TEXT'])
        self.screen.blit(txt, (bx + 15, by + 10))

    def _render_game_over(self, context):
        if not context.game_over: return
        
        overlay = pygame.Surface((GAME_PARAMS['SCREEN_WIDTH'], GAME_PARAMS['SCREEN_HEIGHT']), pygame.SRCALPHA)
        overlay.fill(COLORS['NOTICE_BG'])
        self.screen.blit(overlay, (0, 0))

        color = COLORS['PLAYER'] if context.winner == "プレイヤー" else COLORS['ENEMY']
        res_text = self.notice_font.render(f"{context.winner}の勝利！", True, color)
        
        center_x = GAME_PARAMS['SCREEN_WIDTH'] // 2
        center_y = GAME_PARAMS['SCREEN_HEIGHT'] // 2
        
        tr = res_text.get_rect(center=(center_x, center_y))
        self.screen.blit(res_text, tr)

        restart_text = self.font.render("ESCキーで終了", True, COLORS['TEXT'])
        rr = restart_text.get_rect(center=(center_x, center_y + GAME_PARAMS['NOTICE_Y_OFFSET']))
        self.screen.blit(restart_text, rr)
