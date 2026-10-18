"""シーン管理を統括するクラス（型付き遷移・イベント一元集約）"""

from typing import Dict, Optional, Type, Any
from dataclasses import dataclass, field
import logging
import pygame

from core.constants import SceneId
from core.inputs import InputState, EventReaderProtocol
from domain.models import GameDataProtocol, SaveDataProtocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SceneTransition:
    """型付きシーン遷移指示オブジェクト"""
    next_scene: Optional[SceneId] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    should_quit: bool = False

    @classmethod
    def to(cls, scene_id: SceneId, **payload) -> 'SceneTransition':
        return cls(next_scene=scene_id, payload=payload)

    @classmethod
    def quit(cls) -> 'SceneTransition':
        return cls(should_quit=True)

    @classmethod
    def stay(cls) -> 'SceneTransition':
        return cls()


@dataclass
class SceneContext:
    """シーン間で共有される依存関係"""
    screen: Optional[pygame.Surface]
    data_manager: GameDataProtocol
    save_manager: SaveDataProtocol


class Scene:
    """全てのシーンの基底クラス"""
    def __init__(self, ctx: SceneContext):
        self.ctx = ctx
        self.screen = ctx.screen

    def on_enter(self, **payload):
        """シーン遷移時の引数受け取りフック"""
        pass

    def on_exit(self):
        """シーン終了・破棄時のクリーンアップフック"""
        pass

    def handle_input(self, input_state: InputState) -> SceneTransition:
        """論理入力を処理し、遷移シグナルを返す"""
        return SceneTransition.stay()

    def update(self, dt: float):
        pass

    def render(self):
        pass


class SceneManager:
    """シーンのライフサイクルと遷移を一元管理する"""

    def __init__(self, ctx: SceneContext, event_reader: EventReaderProtocol):
        self.ctx = ctx
        self.event_reader = event_reader
        self.scene_classes: Dict[SceneId, Type[Scene]] = {}
        self.current_scene: Optional[Scene] = None

    def register_scene(self, tag: SceneId, scene_class: Type[Scene]):
        self.scene_classes[tag] = scene_class

    def switch_to(self, tag: SceneId, **payload):
        scene_class = self.scene_classes.get(tag)
        if not scene_class:
            logger.error(f"Scene tag '{tag}' not found.")
            return

        if self.current_scene is not None:
            self.current_scene.on_exit()

        self.current_scene = scene_class(self.ctx)
        self.current_scene.on_enter(**payload)

    def process_frame(self, dt: float) -> bool:
        """1フレームのイベント処理・更新・描画を一元実行。False でゲーム終了"""
        if not self.event_reader.handle_events():
            return False

        if not self.current_scene:
            return True

        transition = self.current_scene.handle_input(self.event_reader.state)
        if transition.should_quit:
            return False
        if transition.next_scene:
            self.switch_to(transition.next_scene, **transition.payload)
            return True

        self.current_scene.update(dt)
        self.current_scene.render()
        return True
