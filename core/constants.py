"""core 層で共通の定数・識別子定義"""
from enum import Enum


class SceneId(str, Enum):
    """シーン識別子"""
    TITLE = "title"
    BATTLE = "battle"
    CUSTOMIZE = "customize"
