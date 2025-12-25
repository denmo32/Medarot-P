"""戦闘システム"""

import random
from core.ecs import System
from components.battle import GaugeComponent, PartListComponent, HealthComponent, AttackComponent, DefeatedComponent
from battle.utils import calculate_action_times

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
        defeated_comp = components.get('defeated')
        if not defeated_comp or defeated_comp.is_defeated:
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

        part_list_comp = attacker_comps.get('partlist')
        target_part_list_comp = target_comps.get('partlist')

        if not part_list_comp or not target_part_list_comp: return 0

        # 攻撃者のパーツから攻撃力を取得
        attacker_part_id = part_list_comp.parts.get(part)
        if not attacker_part_id: return 0

        attacker_part_comps = self.world.entities.get(attacker_part_id)
        if not attacker_part_comps: return 0

        attack_comp = attacker_part_comps.get('attack')
        if not attack_comp: return 0

        power = attack_comp.attack

        # ターゲットパーツの決定（ランダム）
        target_part_types = list(target_part_list_comp.parts.keys())
        t_part = random.choice(target_part_types)

        target_part_id = target_part_list_comp.parts.get(t_part)
        if not target_part_id: return 0

        target_part_comps = self.world.entities.get(target_part_id)
        if not target_part_comps: return 0

        health_comp = target_part_comps.get('health')
        if not health_comp: return 0

        damage = random.randint(int(power * 0.8), int(power * 1.2))

        # ダメージ適用
        health_comp.hp = max(0, health_comp.hp - damage)

        # Medabot全体の敗北判定（頭部が0になったら）
        if t_part == "head" and health_comp.hp <= 0:
            target_defeated_comp = target_comps.get('defeated')
            if target_defeated_comp:
                target_defeated_comp.is_defeated = True

        return damage

    def _get_random_alive_target(self, my_team: str):
        target_team = "enemy" if my_team == "player" else "player"
        alive = []
        for eid, comps in self.world.entities.items():
            team = comps.get('team')
            part_list = comps.get('partlist')
            if team and team.team_type == target_team and part_list:
                # 頭部のHPを確認
                head_part_id = part_list.parts.get('head')
                if head_part_id:
                    head_comps = self.world.entities.get(head_part_id)
                    if head_comps:
                        health = head_comps.get('health')
                        if health and health.hp > 0:
                            alive.append((eid, comps))
        return random.choice(alive) if alive else None

    def _handle_enemy_ai(self, entity_id):
        comps = self.world.entities[entity_id]
        part_list_comp = comps.get('partlist')
        gauge_comp = comps.get('gauge')

        if not part_list_comp or not gauge_comp: return

        # 使用可能なパーツを確認（攻撃力のあるパーツ）
        available = []
        for part_type, part_id in part_list_comp.parts.items():
            if part_type == "leg": continue  # 脚部は攻撃不可
            part_comps = self.world.entities.get(part_id)
            if part_comps:
                health = part_comps.get('health')
                if health and health.hp > 0:
                    available.append(part_type)

        if available:
            gauge_comp.selected_part = random.choice(available)
            gauge_comp.selected_action = "attack"
            
            # 選択したパーツの攻撃力に応じてチャージ/クールダウン時間を設定
            selected_part_id = part_list_comp.parts.get(gauge_comp.selected_part)
            if selected_part_id:
                selected_part_comps = self.world.entities.get(selected_part_id)
                if selected_part_comps:
                    attack_comp = selected_part_comps.get('attack')
                    if attack_comp:
                        charging_time, cooldown_time = calculate_action_times(attack_comp.attack)
                        gauge_comp.charging_time = charging_time
                        gauge_comp.cooldown_time = cooldown_time
        else:
            gauge_comp.selected_action = "skip"

        # 状態遷移
        gauge_comp.status = GaugeComponent.CHARGING
        gauge_comp.progress = 0.0
