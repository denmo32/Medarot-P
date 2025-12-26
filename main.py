"""Medarot-P メインエントリーポイント - シーン管理"""

import pygame
import sys
import traceback
from config import SCREEN_WIDTH, SCREEN_HEIGHT, GAME_PARAMS
from scenes.title_scene import TitleScene
from scenes.battle_scene import BattleScene
from scenes.customize_scene import CustomizeScene

# pygameの初期化
pygame.init()

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Medarot-P")

    # シーン管理
    current_scene_tag = 'title'
    scenes = {
        'title': TitleScene(screen),
        'battle': None,
        'customize': None
    }
    
    clock = pygame.time.Clock()
    running = True
    
    try:
        while running:
            # 1. デルタタイム計算
            dt = min(clock.tick(GAME_PARAMS['FPS']) / 1000.0, 1.0 / GAME_PARAMS['FPS'])

            # 2. 現在のシーンの取得と初期化（必要な場合のみ）
            if scenes[current_scene_tag] is None:
                if current_scene_tag == 'battle':
                    scenes['battle'] = BattleScene(screen)
                elif current_scene_tag == 'customize':
                    scenes['customize'] = CustomizeScene(screen)
                elif current_scene_tag == 'title':
                    scenes['title'] = TitleScene(screen)

            scene = scenes[current_scene_tag]

            # 3. イベント処理
            action = scene.handle_events()
            
            if action == 'quit':
                running = False
            elif action in scenes:
                # シーン遷移
                current_scene_tag = action
                # 遷移先のシーンを一度破棄して再生成させる（最新データを反映するため）
                scenes[action] = None 
            
            # 4. 更新と描画
            if running and scene:
                scene.update(dt)
                scene.render()

    except KeyboardInterrupt:
        pass
    except Exception:
        # 予期せぬエラーが発生した場合、スタックトレースを表示して終了
        print("=== 予期せぬエラーが発生しました ===", file=sys.stderr)
        traceback.print_exc()
    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()