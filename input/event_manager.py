"""イベント管理クラス（ECS入力ブリッジ）"""

import pygame
from core.ecs import World
from components.input import InputComponent

class EventManager:
    """PygameイベントをInputComponentに変換するクラス"""
    
    def __init__(self, world: World):
        self.world = world
        self.input_entity_id = None
        # InputComponentを持つエンティティを探す、なければ作る
        inputs = self.world.get_entities_with_components('input')
        if inputs:
            self.input_entity_id = inputs[0][0]
        else:
            entity = self.world.create_entity()
            self.world.add_component(entity.id, InputComponent())
            self.input_entity_id = entity.id

    def handle_events(self) -> bool:
        """
        イベントを処理し、InputComponentを更新する。
        ゲーム終了時はFalseを返す。
        """
        input_comp = self.world.entities[self.input_entity_id]['input']
        
        # フレームごとのリセット
        input_comp.mouse_clicked = False
        input_comp.escape_pressed = False
        
        # 現在のマウス位置を取得
        mx, my = pygame.mouse.get_pos()
        input_comp.mouse_x = mx
        input_comp.mouse_y = my

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左クリック
                    input_comp.mouse_clicked = True
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    input_comp.escape_pressed = True
        
        return True
