"""イベント管理クラス（ECS入力ブリッジ）"""

import pygame
from core.ecs import World
from components.input_component import InputComponent

class EventManager:
    """Pygameイベントを論理入力（InputComponent）に変換する"""
    def __init__(self, world: World):
        self.world = world
        inputs = self.world.get_entities_with_components('input')
        if inputs:
            self.input_entity_id = inputs[0][0]
        else:
            self.input_entity_id = self.world.create_entity()
            self.world.add_component(self.input_entity_id, InputComponent())

    def handle_events(self) -> bool:
        """
        イベントを処理し、InputComponentを更新する。
        戻り値: Falseならアプリケーション終了シグナル
        """
        input_comp = self.world.entities[self.input_entity_id]['input']
        
        # フレームごとのリセット
        input_comp.mouse_clicked = False
        input_comp.btn_ok = False
        input_comp.btn_cancel = False
        input_comp.btn_menu = False
        input_comp.btn_left = False
        input_comp.btn_right = False
        input_comp.btn_up = False
        input_comp.btn_down = False
        
        # マウス位置更新
        mx, my = pygame.mouse.get_pos()
        input_comp.mouse_x, input_comp.mouse_y = mx, my

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    input_comp.mouse_clicked = True
                    # マウス操作も決定扱いとするケースがあるため、状況に応じてbtn_okも立てる運用も可能だが
                    # ここではクリックはクリックとして独立させ、UI側で「クリック or btn_ok」判定を行う方針とする。
            
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