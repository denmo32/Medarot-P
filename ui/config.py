"""UI関連の設定値"""

# 画面設定（デフォルト基準値）
# 起動時のサイズだが、ロジック上は比率計算の基準としてのみ意識される
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 600

# 色の定義
COLORS = {
    'BACKGROUND': (50, 50, 50),
    'PLAYER': (0, 100, 200),
    'ENEMY': (200, 0, 0),
    'BAR_BG': (100, 100, 100),
    'BAR_FG': (0, 200, 0),
    'HP_BG': (80, 0, 0),
    'HP_GAUGE': (50, 255, 100),
    'TEXT': (255, 255, 255),
    'NOTICE_BG': (0, 0, 0, 180),
    'BUTTON_BG': (150, 150, 150),
    'BUTTON_DISABLED_BG': (80, 80, 80),
    'BUTTON_BORDER': (0, 0, 0),
    'GUIDE_LINE': (120, 120, 120),
    'HOME_MARKER': (100, 100, 100),
    'BORDER_CHARGE': (255, 150, 0),
    'BORDER_COOLDOWN': (0, 200, 255),
    'BORDER_WAIT': (255, 255, 255),
    'PANEL_BG': (35, 45, 60),
    'PANEL_BORDER': (60, 70, 90),
    'SELECT_HIGHLIGHT': (0, 150, 255),
}

# フォント設定
FONT_NAMES = ['ui/assets/fonts/NotoSansJP-Regular.ttf']

# レイアウトパラメータ (比率定義 0.0 ~ 1.0)
UI_PARAMS = {
    # フィールド配置 (Screen Width/Heightに対する比率)
    'PLAYER_TEAM_X_RATIO': 0.06,  # 左端からの位置
    'ENEMY_TEAM_X_RATIO': 0.56,   # 左端からの位置 (56%地点)
    'TEAM_Y_START_RATIO': 0.1,    # 上端からの開始位置
    'CHAR_SPACING_RATIO': 0.22,   # キャラクター間の縦間隔
    
    'GAUGE_WIDTH_RATIO': 0.38,    # ゲージ長さ
    'GAUGE_HEIGHT_RATIO': 0.06,

    # メッセージウィンドウ
    'MESSAGE_WINDOW_Y_RATIO': 0.75,
    'MESSAGE_WINDOW_HEIGHT_RATIO': 0.25,
    'MESSAGE_WINDOW_PADDING_RATIO': 0.012,
    'MESSAGE_WINDOW_BG_COLOR': (30, 30, 30),
    'MESSAGE_WINDOW_BORDER_COLOR': (100, 100, 100),
    
    'LOG_DISPLAY_LINES': 1,
    
    'UI': {
        'BTN_WIDTH_RATIO': 0.25,
        'BTN_HEIGHT_RATIO': 0.075,
        'BTN_PADDING_RATIO': 0.012,
    },
    
    'CUSTOMIZE': {
        'PANEL_PADDING_RATIO': 0.02,
        'PANEL_Y_RATIO': 0.07,
        'PANEL_HEIGHT_RATIO': 0.86,
        'COLUMN_1_WIDTH_RATIO': 0.22,
        'COLUMN_2_WIDTH_RATIO': 0.38,
        'COLUMN_3_WIDTH_RATIO': 0.32,
    }
}

# チームごとの設定（カラー）
from domain.constants import TeamType, PartType
TEAM_SETTINGS = {
    TeamType.PLAYER: {
        'color': COLORS['PLAYER']
    },
    TeamType.ENEMY: {
        'color': COLORS['ENEMY']
    }
}

PART_LABELS = {
    PartType.HEAD: "頭部",
    PartType.RIGHT_ARM: "右腕",
    PartType.LEFT_ARM: "左腕",
    PartType.LEGS: "脚部"
}

MENU_PART_ORDER = [PartType.HEAD, PartType.RIGHT_ARM, PartType.LEFT_ARM]