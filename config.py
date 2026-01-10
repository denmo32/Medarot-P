# ATBバトルシステムの設定ファイル

# 画面設定
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# 色の定義
COLORS = {
    'BACKGROUND': (50, 50, 50),      # 暗灰色
    'PLAYER': (0, 100, 200),         # プレイヤー用青
    'ENEMY': (200, 0, 0),            # エネミー用赤
    'BAR_BG': (100, 100, 100),       # ゲージ背景色
    'BAR_FG': (0, 200, 0),           # ゲージ進行色
    'HP_BAR': (255, 0, 0),           # HPバー色（旧式）
    'HP_HEAD': (255, 0, 0),          # 頭部HPバー色
    'HP_RIGHT_ARM': (0, 0, 255),     # 右腕HPバー色
    'HP_LEFT_ARM': (0, 255, 255),    # 左腕HPバー色
    'HP_LEG': (255, 255, 0),         # 脚部HPバー色
    'HP_BG': (80, 0, 0),             # HP背景色（暗い赤）
    'HP_GAUGE': (50, 255, 100),      # HPゲージ色（明るい緑）
    'TEXT': (255, 255, 255),         # テキスト色
    'NOTICE_BG': (0, 0, 0, 180),     # 通知背景色
    'BUTTON_BG': (150, 150, 150),    # ボタン背景色
    'BUTTON_DISABLED_BG': (80, 80, 80),  # 無効状態ボタン色
    'BUTTON_BORDER': (0, 0, 0),      # ボタン境界色
    'GUIDE_LINE': (120, 120, 120),   # ガイドライン色
    'HOME_MARKER': (100, 100, 100),  # ホームポジションマーカー色
    # カスタマイズ画面用
    'PANEL_BG': (35, 45, 60),        # パネル背景色
    'PANEL_BORDER': (60, 70, 90),    # パネル枠線
    'SELECT_HIGHLIGHT': (0, 150, 255), # 選択ハイライト
}

# フォント設定
FONT_NAMES = ['meiryo', 'yumin', 'msmincho', 'msgothic', 'Noto Sans CJK JP', 'Noto Sans Japanese', 'sans-serif']

# ゲームパラメータ
GAME_PARAMS = {
    'FPS': 60,
    'PLAYER_COUNT': 3,
    'ENEMY_COUNT': 3,
    'PLAYER_TEAM_X': 50,
    'ENEMY_TEAM_X': 450,
    'TEAM_Y_OFFSET': 60,      # 上部の余白を活用して開始位置を上げる (100 -> 60)
    'CHARACTER_SPACING': 135, # 配置間隔を広げる (120 -> 135)
    'GAUGE_WIDTH': 300,
    'GAUGE_HEIGHT': 40,
    'HP_BAR_WIDTH': 30,
    'HP_BAR_HEIGHT': 15,
    'HP_BAR_Y_OFFSET': 50,
    'LOG_DISPLAY_LINES': 1,
    'LOG_Y_OFFSET': 120,
    'CLICK_MESSAGE_Y': 30,
    'NOTICE_Y_OFFSET': 50,
    'SCREEN_WIDTH': 800,
    'SCREEN_HEIGHT': 600,
    'MESSAGE_WINDOW_HEIGHT': 150,
    'MESSAGE_WINDOW_Y': 450,
    'MESSAGE_WINDOW_BG_COLOR': (30, 30, 30),
    'MESSAGE_WINDOW_BORDER_COLOR': (100, 100, 100),
    'MESSAGE_WINDOW_PADDING': 10,
    'UI': {
        'BTN_WIDTH': 80,
        'BTN_HEIGHT': 40,
        'BTN_PADDING': 10,
        'BTN_Y_OFFSET': 60,
        'TURN_TEXT_Y_OFFSET': 100,
        'NEXT_MSG_X_OFFSET': 250,
        'NEXT_MSG_Y_OFFSET': 30,
    },
    'CUSTOMIZE': {
        'PANEL_PADDING': 15,
        'COLUMN_1_WIDTH': 180,
        'COLUMN_2_WIDTH': 300,
        'COLUMN_3_WIDTH': 260,
        'PANEL_Y': 40,
        'PANEL_HEIGHT': 520,
    }
}