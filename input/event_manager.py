"""イベント管理クラス（ECS入力ブリッジ）"""

import pygame
from core.ecs import World
from components.input import InputComponent

class EventManager:
    """PygameイベントをInputComponentに変換する"""
    def __init__(self, world: World):
        self.world = world
        inputs = self.world.get_entities_with_components('input')
        if inputs:
            self.input_entity_id = inputs[0][0]
        else:
            self.input_entity_id = self.world.create_entity()
            self.world.add_component(self.input_entity_id, InputComponent())

    def handle_events(self) -> bool:
        input_comp = self.world.entities[self.input_entity_id]['input']
        input_comp.mouse_clicked = False
        input_comp.escape_pressed = False
        input_comp.key_z = False
        input_comp.key_x = False
        input_comp.key_left = False
        input_comp.key_right = False
        input_comp.key_up = False
        input_comp.key_down = False
        
        mx, my = pygame.mouse.get_pos()
        input_comp.mouse_x, input_comp.mouse_y = mx, my

        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: input_comp.mouse_clicked = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: input_comp.escape_pressed = True
                elif event.key == pygame.K_z: input_comp.key_z = True
                elif event.key == pygame.K_x: input_comp.key_x = True
                elif event.key in (pygame.K_LEFT, pygame.K_a): input_comp.key_left = True
                elif event.key in (pygame.K_RIGHT, pygame.K_d): input_comp.key_right = True
                elif event.key in (pygame.K_UP, pygame.K_w): input_comp.key_up = True
                elif event.key in (pygame.K_DOWN, pygame.K_s): input_comp.key_down = True
        return True