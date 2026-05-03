import pygame
from core.utils import resource_path

class FontProvider:
    _cache = {}

    @classmethod
    def get(cls, path: str, size: int, scale: float) -> pygame.font.Font:
        """スケールに応じたフォントを取得し、キャッシュする"""
        key = (path, size, scale)
        if key not in cls._cache:
            cls._cache[key] = pygame.font.Font(resource_path(path), int(size * scale))
        return cls._cache[key]

    @classmethod
    def clear_cache(cls):
        """全キャッシュをクリアする"""
        cls._cache.clear()
