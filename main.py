"""Medarot-P バトルシステム - メインエントリーポイント"""

import pygame
import sys
from config import SCREEN_WIDTH, SCREEN_HEIGHT, GAME_PARAMS
from battle.manager import BattleSystem
from input.event_manager import EventManager

# pygameの初期化
pygame.init()

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Medarot-P Battle System (Full ECS)")

    # バトルシステムの初期化（screenを渡してRenderSystemを内部で構築）
    battle_system = BattleSystem(
        screen,
        player_count=GAME_PARAMS['PLAYER_COUNT'],
        enemy_count=GAME_PARAMS['ENEMY_COUNT']
    )

    # InputComponentへのイベントブリッジ
    event_manager = EventManager(battle_system.world)
    
    clock = pygame.time.Clock()
    running = True
    
    try:
        while running:
            # 1. 入力イベント収集 -> InputComponent更新
            running = event_manager.handle_events()
            
            # 2. デルタタイム計算
            dt = min(clock.tick(GAME_PARAMS['FPS']) / 1000.0, 1.0 / GAME_PARAMS['FPS'])

            # 3. ECSシステム一括更新 (Input -> Logic -> Render)
            battle_system.update(dt)

            # 描画処理はRenderSystem内で行われるため、ここには記述不要

    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()