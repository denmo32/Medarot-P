"""Medarot-P メインエントリーポイント - シーン管理"""

import logging
import pygame
import sys
import traceback
from domain.constants import SceneId
from ui.config import SCREEN_WIDTH, SCREEN_HEIGHT
from domain.config import FPS
from scenes.title_scene import TitleScene
from scenes.battle_scene import BattleScene
from scenes.customize_scene import CustomizeScene
from data.game_data_manager import GameDataManager
from data.save_data_manager import SaveDataManager
from core.scene_manager import SceneManager, SceneContext
from infra.event_reader import PygameEventReader

logging.basicConfig(level=logging.INFO, format="%(levelname)s: [%(name)s] %(message)s")
pygame.init()


def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Medarot-P")

    # データリポジトリおよびイベントリーダー（具象アダプター）の生成
    data_manager = GameDataManager()
    save_manager = SaveDataManager(data_manager)
    event_reader = PygameEventReader()

    ctx = SceneContext(screen, data_manager, save_manager)

    # Composition Root において、依存性を明示的に注入
    manager = SceneManager(ctx, event_reader=event_reader)
    manager.register_scene(SceneId.TITLE, TitleScene)
    manager.register_scene(SceneId.BATTLE, BattleScene)
    manager.register_scene(SceneId.CUSTOMIZE, CustomizeScene)

    manager.switch_to(SceneId.TITLE)

    clock = pygame.time.Clock()
    running = True

    try:
        while running:
            dt = min(clock.tick(FPS) / 1000.0, 1.0 / FPS)
            # 入力・更新・描画を一元処理
            running = manager.process_frame(dt)
    except KeyboardInterrupt:
        pass
    except Exception:
        print("=== 予期せぬエラーが発生しました ===", file=sys.stderr)
        traceback.print_exc()
    finally:
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    main()