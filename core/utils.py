import os
import sys

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        if getattr(sys, 'frozen', False):
             # One-dir mode
             base_path = os.path.dirname(sys.executable)
             # PyInstaller 6+ uses _internal folder
             internal_path = os.path.join(base_path, '_internal')
             if os.path.exists(internal_path):
                 base_path = internal_path
        else:
             base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)



def get_save_path(relative_path):

    """Get absolute path to save data, works for dev and for PyInstaller (outside _MEIPASS)"""

    if getattr(sys, 'frozen', False):

        # The application is frozen (bundled)

        # Store save data in the same directory as the executable

        base_path = os.path.dirname(sys.executable)

    else:

        # The application is running in a normal Python environment

        base_path = os.path.abspath(".")



    full_path = os.path.join(base_path, relative_path)

    # Ensure the directory exists

    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    return full_path
