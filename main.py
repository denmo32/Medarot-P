"""Medarot-P メインエントリーポイント - シーン管理"""

import pygame
import sys
from config import SCREEN_WIDTH, SCREEN_HEIGHT, GAME_PARAMS
from scenes.title_scene import TitleScene
from scenes.battle_scene import BattleScene
from scenes.customize_scene import CustomizeScene

# pygameの初期化
pygame.init()

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Medarot-P")

    # 初期シーンをタイトル画面に設定
    current_scene = 'title'
    title_scene = TitleScene(screen)
    battle_scene = BattleScene(screen)
    customize_scene = CustomizeScene(screen)
    
    clock = pygame.time.Clock()
    running = True
    
    try:
        while running:
            # 1. デルタタイム計算
            dt = min(clock.tick(GAME_PARAMS['FPS']) / 1000.0, 1.0 / GAME_PARAMS['FPS'])

            # 2. 現在のシーンに応じてイベント処理
            if current_scene == 'title':
                action = title_scene.handle_events()
                if action == 'battle':
                    current_scene = 'battle'
                elif action == 'customize':
                    current_scene = 'customize'
                elif action == 'quit':
                    running = False
            elif current_scene == 'battle':
                action = battle_scene.handle_events()
                if action == 'title':
                    current_scene = 'title'
                elif action == 'quit':
                    running = False
            elif current_scene == 'customize':
                action = customize_scene.handle_events()
                if action == 'title':
                    current_scene = 'title'
                elif action == 'quit':
                    running = False

            # 3. 現在のシーンの更新
            if current_scene == 'title':
                title_scene.update(dt)
            elif current_scene == 'battle':
                battle_scene.update(dt)
            elif current_scene == 'customize':
                customize_scene.update(dt)

            # 4. 現在のシーンの描画
            if current_scene == 'title':
                title_scene.render()
            elif current_scene == 'battle':
                battle_scene.render()
            elif current_scene == 'customize':
                customize_scene.render()

    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
