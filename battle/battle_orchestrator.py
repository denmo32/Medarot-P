"""ECSアーキテクチャに基づくバトルシステム構成"""

from core.ecs import World
from battle.battle_entity_factory import BattleEntityFactory
from domain.config import PLAYER_COUNT, ENEMY_COUNT
from data.game_data_manager import GameDataManager
from data.save_data_manager import SaveDataManager

# Systems (Logic)
# Decision
from battle.systems.decision.input_system import InputSystem
from battle.systems.decision.ai_system import AISystem
from battle.systems.decision.target_selection_system import TargetSelectionSystem
# Gauge
from battle.systems.gauge.gauge_system import GaugeSystem
# Phase
from battle.systems.phase.turn_system import TurnSystem
from battle.systems.phase.battle_flow_system import BattleFlowSystem
from battle.systems.phase.battle_status_system import BattleStatusSystem
# Pacing
from battle.systems.pacing.target_indicator_system import TargetIndicatorSystem
from battle.systems.pacing.cutin_flow_system import CutinFlowSystem
# Action
from battle.systems.action.action_command_system import ActionCommandSystem
from battle.systems.action.action_initiation_system import ActionInitiationSystem
from battle.systems.action.combat_calculation_system import CombatCalculationSystem
from battle.systems.action.action_resolution_system import ActionResolutionSystem
# Impact
from battle.systems.impact.damage_system import DamageSystem
from battle.systems.impact.destruction_system import DestructionSystem

# ViewModel and Systems (UI Layer)
from ui.battle.view_model import BattleViewModel

class BattleEngine:
    def __init__(self,
                 data_manager: GameDataManager,
                 save_manager: SaveDataManager,
                 ui_params: dict,
                 player_count: int = PLAYER_COUNT,
                 enemy_count: int = ENEMY_COUNT):

        self.data_manager = data_manager
        self.save_manager = save_manager

        self.world = World()
        self.context_entity_id = BattleEntityFactory.create_battle_context(self.world)
        BattleEntityFactory.create_input_manager(self.world)
        
        # UI設定から比率パラメータを渡す（外部から注入されたui_paramsを使用）
        BattleEntityFactory.create_teams(self.world, player_count, enemy_count,
            ui_params['PLAYER_TEAM_X_RATIO'], 
            ui_params['ENEMY_TEAM_X_RATIO'],
            ui_params['TEAM_Y_START_RATIO'], 
            ui_params['CHAR_SPACING_RATIO'],
            self.data_manager, self.save_manager
        )
        
        # 描画と入力解釈で共有するViewModelを生成
        self.view_model = BattleViewModel(self.world)
        
        self.systems = [
            # === 1. 意思決定・事前準備 ===
            InputSystem(self.world),              # 物理入力→論理コマンド変換
            AISystem(self.world),                 # エネミー行動決定
            TargetSelectionSystem(self.world),    # 射撃特性のターゲット事前選定（IDLE時）

            # === 2. コマンド受理・ゲージ進行 ===
            ActionCommandSystem(self.world),      # ActionCommand消費→ゲージをCHARGING化
            GaugeSystem(self.world),              # ゲージ進行・充填完了判定・待機キュー管理

            # === 3. ターン制御・フェーズ遷移 ===
            TurnSystem(self.world),               # キュー先頭取得→INPUT/ENEMY_TURNへ遷移
            BattleFlowSystem(self.world),         # 開始演出・LOG_WAIT制御・IDLE復復
            BattleStatusSystem(self.world),       # 勝敗判定（IDLE時のみ実行）

            # === 4. 行動実行パイプライン ===
            ActionInitiationSystem(self.world),   # 充填完了検知→ActionEvent生成
            CombatCalculationSystem(self.world),  # 命中・ダメージ・特性計算（ActionEventへ追記）

            # === 5. 演出同期・フェーズ進行 ===
            TargetIndicatorSystem(self.world),    # ターゲット指示タイマー→EXECUTING等へ遷移
            CutinFlowSystem(self.world),          # カットインタイマー→EXECUTINGへ遷移

            # === 6. 結果解決・物理適用 ===
            ActionResolutionSystem(self.world),   # EXECUTINGフェーズで結果取りまとめ→DamageEvent生成
            DamageSystem(self.world),             # HP減算・状態異常付与・PartDestroyedEvent生成
            DestructionSystem(self.world)        # 部位破壊検知→機能停止フラグ付与
        ]

    def update(self, dt: float = 0.016) -> None:
        for system in self.systems:
            system.update(dt)
