"""プラットフォーム・ファイルシステム関連ユーティリティ"""
import os
import sys


def resource_path(relative_path: str) -> str:
    """リソースパスを取得（開発環境および PyInstaller 展開時対応）"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        if getattr(sys, 'frozen', False):
            base_path = os.path.join(os.path.dirname(sys.executable), '_internal')
            if not os.path.exists(base_path):
                base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_user_data_path(filename: str = "save_data.json") -> str:
    """OS標準のユーザーデータ保存先ディレクトリを取得"""
    app_name = "Medarot-P"
    if sys.platform == "win32":
        base_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
        user_dir = os.path.join(base_dir, app_name)
    elif sys.platform == "darwin":
        user_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", app_name)
    else:
        user_dir = os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")), app_name)

    full_path = os.path.join(user_dir, filename)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    return full_path
