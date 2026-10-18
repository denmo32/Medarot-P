"""Medarot-P メインエントリーポイント - シーン管理"""

import logging
import pygame
import sys
from core.constants import SceneId
from ui.config import SCREEN_WIDTH, SCREEN_HEIGHT
from domain.config import FPS
from scenes.title_scene import TitleScene
from scenes.battle_scene import BattleScene
from scenes.customize_scene import CustomizeScene
from data.game_data_manager import GameDataManager
from data.save_data_manager import SaveDataManager
from core.scene_manager import SceneManager, SceneContext
from infra.event_reader import PygameEventReader

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: [%(name)s] %(message)s")
pygame.init()

# ウィンドウ移動などの極端なラグスパイク時のみ上限を制限するクランプ値（10FPS相当）
MAX_DELTA_TIME = 0.1


def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Medarot-P")

    data_manager = GameDataManager()
    save_manager = SaveDataManager(data_manager)
    event_reader = PygameEventReader()

    ctx = SceneContext(
        data_manager=data_manager,
        save_manager=save_manager,
        screen=screen,
    )

    manager = SceneManager(ctx, event_reader=event_reader)
    manager.register_scene(SceneId.TITLE, TitleScene)
    manager.register_scene(SceneId.BATTLE, BattleScene)
    manager.register_scene(SceneId.CUSTOMIZE, CustomizeScene)

    manager.switch_to(SceneId.TITLE)

    clock = pygame.time.Clock()
    running = True
    exit_code = 0

    try:
        while running:
            raw_dt = clock.tick(FPS) / 1000.0
            dt = min(raw_dt, MAX_DELTA_TIME)
            running = manager.process_frame(dt)
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.exception("予期せぬエラーが発生しました")
        exit_code = 1
    finally:
        pygame.quit()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()