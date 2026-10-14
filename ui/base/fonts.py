import pygame
from infra.paths import resource_path


class FontProvider:
    _cache = {}

    @classmethod
    def get(cls, path: str, size: int, scale: float = 1.0) -> pygame.font.Font:
        """スケールに応じたフォントを取得し、整数サイズで安全にキャッシュする"""
        scaled_size = max(1, int(round(size * scale)))
        key = (path, scaled_size)  # float をキーに含めない

        if key not in cls._cache:
            cls._cache[key] = pygame.font.Font(resource_path(path), scaled_size)
        return cls._cache[key]
