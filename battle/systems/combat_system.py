"""戦闘システム"""

import random
from core.ecs import System
from components.battle import GaugeComponent

class CombatSystem(System):
    """戦闘システム：AI思考と攻撃実行を担当"""
    
    def update(self, dt: float = 0.016):
        # バトルコンテキスト取得
        contexts = self.world.get_entities_with_components('battlecontext')
        if not contexts: return
        context = contexts[0][1]['battlecontext']

        # UI操作でブロックされている場合は何もしない
        if context.waiting_for_input or context.game_over or context.waiting_for_action:
            return

        # 待機キューの確認
        if not context.waiting_queue:
            return

        # キュー先頭のエンティティを取得
        entity_id = context.waiting_queue[0]
        
        # エンティティが存在するか、既に倒されていないかチェック
        if entity_id not in self.world.entities:
            context.waiting_queue.pop(0)
            return
            
        components = self.world.entities[entity_id]
        hp_comp = components.get('parthealth')
        if not hp_comp or hp_comp.is_defeated:
            context.waiting_queue.pop(0)
            return

        gauge_comp = components.get('gauge')
        team_comp = components.get('team')
        name_comp = components.get('name')

        if not gauge_comp or not team_comp or not name_comp:
            context.waiting_queue.pop(0)
            return

        # --- 状態ごとの処理 ---

        # 1. チャージ完了 -> 行動実行
        if gauge_comp.status == GaugeComponent.CHARGING and gauge_comp.progress >= 100.0:
            self._execute_action(entity_id, context, gauge_comp, name_comp, team_comp)
            # 行動後はクールダウンへ
            gauge_comp.status = GaugeComponent.COOLDOWN
            gauge_comp.progress = 0.0
            gauge_comp.selected_action = None
            gauge_comp.selected_part = None
            # キューから外す
            if context.waiting_queue and context.waiting_queue[0] == entity_id:
                context.waiting_queue.pop(0)

        # 2. クールダウン完了 -> 行動選択開始
        elif gauge_comp.status == GaugeComponent.ACTION_CHOICE:
            context.current_turn_entity_id = entity_id
            
            if team_comp.team_type == "player":
                # プレイヤーなら入力待ちへ
                context.waiting_for_action = True
            else:
                # エネミーならAI思考
                self._handle_enemy_ai(entity_id)
                # AIは即時決定するのでキューから外す処理はGaugeSystem側で管理されるべきだが、
                # ここで決定した状態(CHARGING)に移行させるため、ループ次周で処理される
                # ただし、ACTION_CHOICE状態のままキューに残るとブロックするので、
                # 状態遷移だけここで行い、キュー操作はGaugeSystemやロジックフローに委ねる
                # 既存ロジックではここでpopしていたが、AI決定後はCHARGINGになるため、
                # キューに残ったままでもCHARGING処理待ちになるはず。
                # ただし、CHARGINGは時間経過が必要なので、キュー先頭をブロックすべきでない。
                # ATBの仕様として「チャージ中」はキューから外れるべきなら外す。
                if context.waiting_queue and context.waiting_queue[0] == entity_id:
                    context.waiting_queue.pop(0)

    def _execute_action(self, entity_id, context, gauge_comp, name_comp, team_comp):
        """行動の実行"""
        gauge_comp.status = GaugeComponent.EXECUTING
        
        if gauge_comp.selected_action == "attack":
            target = self._get_random_alive_target(team_comp.team_type)
            if target:
                target_id, target_comps = target
                damage = self._calculate_and_apply_damage(entity_id, target_id, gauge_comp.selected_part)
                
                target_name = target_comps['name'].name
                msg = f"{name_comp.name}が{target_name}に{damage}のダメージ！"
                context.battle_log.append(msg)
                context.waiting_for_input = True # メッセージ確認待ちへ
        
        elif gauge_comp.selected_action == "skip":
            msg = f"{name_comp.name}は行動をスキップ！"
            context.battle_log.append(msg)
            context.waiting_for_input = True

    def _calculate_and_apply_damage(self, attacker_id: int, target_id: int, part: str) -> int:
        attacker_comps = self.world.entities[attacker_id]
        target_comps = self.world.entities[target_id]
        
        atk_comp = attacker_comps.get('partattack')
        hp_comp = target_comps.get('parthealth')

        if not hp_comp or not atk_comp: return 0

        # 攻撃力取得
        power = 0
        if part == "head": power = atk_comp.head_attack
        elif part == "right_arm": power = atk_comp.right_arm_attack
        elif part == "left_arm": power = atk_comp.left_arm_attack
        else: power = 10 # フォールバック

        # ターゲットパーツの決定（ランダム）
        t_part = random.choice(["head", "right_arm", "left_arm", "leg"])
        damage = random.randint(int(power * 0.8), int(power * 1.2))

        # ダメージ適用
        if t_part == "head": hp_comp.head_hp = max(0, hp_comp.head_hp - damage)
        elif t_part == "right_arm": hp_comp.right_arm_hp = max(0, hp_comp.right_arm_hp - damage)
        elif t_part == "left_arm": hp_comp.left_arm_hp = max(0, hp_comp.left_arm_hp - damage)
        elif t_part == "leg": hp_comp.leg_hp = max(0, hp_comp.leg_hp - damage)

        if hp_comp.head_hp <= 0:
            hp_comp.is_defeated = True

        return damage

    def _get_random_alive_target(self, my_team: str):
        target_team = "enemy" if my_team == "player" else "player"
        alive = []
        for eid, comps in self.world.entities.items():
            team = comps.get('team')
            hp = comps.get('parthealth')
            if team and team.team_type == target_team and hp and not hp.is_defeated:
                alive.append((eid, comps))
        return random.choice(alive) if alive else None

    def _handle_enemy_ai(self, entity_id):
        comps = self.world.entities[entity_id]
        hp_comp = comps.get('parthealth')
        gauge_comp = comps.get('gauge')
        
        # 使用可能なパーツを確認
        available = []
        if hp_comp.head_hp > 0: available.append("head")
        if hp_comp.right_arm_hp > 0: available.append("right_arm")
        if hp_comp.left_arm_hp > 0: available.append("left_arm")

        if available:
            gauge_comp.selected_part = random.choice(available)
            gauge_comp.selected_action = "attack"
        else:
            gauge_comp.selected_action = "skip"
        
        # 状態遷移
        gauge_comp.status = GaugeComponent.CHARGING
        gauge_comp.progress = 0.0
