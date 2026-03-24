"""イベント管理クラス（ECS 入力ブリッジ）"""

import pygame
from core.ecs import World
from components.input_component import InputComponent

class EventManager:
    """
    Pygame イベントを論理入力（InputComponent）に変換する。
    
    マウス座標などの「物理入力」を保持するが、
    UI 要素の当たり判定などの「論理解釈」は行わない。
    """
    def __init__(self, world: World):
        self.world = world
        inputs = self.world.get_entities_with_components('input')
        if inputs:
            self.input_entity_id = inputs[0][0]
        else:
            self.input_entity_id = self.world.create_entity()
            self.world.add_component(self.input_entity_id, InputComponent())

        # マウス座標（UI 判定用に Scene 側で参照）
        self.mouse_x: int = 0
        self.mouse_y: int = 0
        self.mouse_clicked: bool = False

    def handle_events(self) -> bool:
        """
        イベントを処理し、InputComponent とマウス状態を更新する。
        戻り値：False ならアプリケーション終了シグナル
        """
        input_comp = self.world.entities[self.input_entity_id]['input']

        # フレームごとのリセット
        input_comp.btn_ok = False
        input_comp.btn_cancel = False
        input_comp.btn_menu = False
        input_comp.btn_left = False
        input_comp.btn_right = False
        input_comp.btn_up = False
        input_comp.btn_down = False
        input_comp.action_commands.clear()
        input_comp.selected_menu_index = None

        self.mouse_clicked = False

        # マウス位置更新（UI 判定用に保持）
        self.mouse_x, self.mouse_y = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.mouse_clicked = True

            elif event.type == pygame.KEYDOWN:
                # 決定
                if event.key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
                    input_comp.btn_ok = True

                # キャンセル
                elif event.key in (pygame.K_x, pygame.K_BACKSPACE):
                    input_comp.btn_cancel = True

                # メニュー / 中断
                elif event.key == pygame.K_ESCAPE:
                    input_comp.btn_menu = True

                # 方向キー
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    input_comp.btn_left = True
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    input_comp.btn_right = True
                elif event.key in (pygame.K_UP, pygame.K_w):
                    input_comp.btn_up = True
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    input_comp.btn_down = True

        return True
