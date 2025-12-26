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
                # AI決定後はチャージ中(CHARGING)になるため、キューから外す
                if context.waiting_queue and context.waiting_queue[0] == entity_id:
                    context.waiting_queue.pop(0)

    def _execute_action(self, entity_id, context, gauge_comp, name_comp, team_comp):
        """行動の実行"""
        gauge_comp.status = GaugeComponent.EXECUTING
        
        # 実行者の表示名（ニックネーム優先）
        attacker_medal = self.world.entities[entity_id].get('medal')
        attacker_name = attacker_medal.nickname if attacker_medal else name_comp.name

        if gauge_comp.selected_action == "attack":
            target = self._get_random_alive_target(team_comp.team_type)
            if target:
                target_id, target_comps = target
                damage, t_part_name = self._calculate_and_apply_damage(entity_id, target_id, gauge_comp.selected_part)
                
                # ターゲットの表示名（ニックネーム優先）
                target_medal = target_comps.get('medal')
                target_display_name = target_medal.nickname if target_medal else target_comps['name'].name
                
                msg = f"{attacker_name}の攻撃！{target_display_name}の{t_part_name}に{damage}のダメージ！"
                context.battle_log.append(msg)
                context.waiting_for_input = True # メッセージ確認待ちへ
        
        elif gauge_comp.selected_action == "skip":
            msg = f"{attacker_name}は行動をスキップ！"
            context.battle_log.append(msg)
            context.waiting_for_input = True

    def _calculate_and_apply_damage(self, attacker_id: int, target_id: int, part: str) -> tuple:
        """ダメージ適用。返り値: (ダメージ量, 命中部位名)"""
        attacker_comps = self.world.entities[attacker_id]
        target_comps = self.world.entities[target_id]

        part_list_comp = attacker_comps.get('partlist')
        target_part_list_comp = target_comps.get('partlist')

        if not part_list_comp or not target_part_list_comp: return 0, "不明"

        # 攻撃者のパーツから攻撃力を取得
        attacker_part_id = part_list_comp.parts.get(part)
        if not attacker_part_id: return 0, "不明"

        attacker_part_comps = self.world.entities.get(attacker_part_id)
        if not attacker_part_comps: return 0, "不明"

        attack_comp = attacker_part_comps.get('attack')
        if not attack_comp: return 0, "不明"

        power = attack_comp.attack

        # ターゲットパーツの決定（生存しているパーツからランダム）
        alive_parts = []
        for p_type, p_id in target_part_list_comp.parts.items():
            p_comps = self.world.entities.get(p_id)
            if p_comps:
                h = p_comps.get('health')
                if h and h.hp > 0:
                    alive_parts.append(p_type)
        
        if not alive_parts: return 0, "不明"
        t_part = random.choice(alive_parts)

        target_part_id = target_part_list_comp.parts.get(t_part)
        target_part_comps = self.world.entities.get(target_part_id)
        health_comp = target_part_comps.get('health')

        damage = random.randint(int(power * 0.8), int(power * 1.2))

        # ダメージ適用
        health_comp.hp = max(0, health_comp.hp - damage)

        # Medabot全体の敗北判定（頭部が0になったら）
        if t_part == "head" and health_comp.hp <= 0:
            target_defeated_comp = target_comps.get('defeated')
            if target_defeated_comp:
                target_defeated_comp.is_defeated = True

        # 部位名の日本語化（簡易）
        names = {"head": "頭部", "right_arm": "右腕", "left_arm": "左腕", "legs": "脚部"}
        return damage, names.get(t_part, t_part)

    def _get_random_alive_target(self, my_team: str):
        target_team = "enemy" if my_team == "player" else "player"
        alive = []
        for eid, comps in self.world.entities.items():
            team = comps.get('team')
            defeated = comps.get('defeated')
            if team and team.team_type == target_team:
                if not defeated or not defeated.is_defeated:
                    alive.append((eid, comps))
        return random.choice(alive) if alive else None

    def _handle_enemy_ai(self, entity_id):
        comps = self.world.entities[entity_id]
        part_list_comp = comps.get('partlist')
        gauge_comp = comps.get('gauge')

        if not part_list_comp or not gauge_comp: return

        # 使用可能なパーツを確認（HPがあり、攻撃力のあるパーツ）
        available = []
        for part_type, part_id in part_list_comp.parts.items():
            if part_type == "legs": continue  # 脚部は攻撃に使わない
            part_comps = self.world.entities.get(part_id)
            if part_comps:
                health = part_comps.get('health')
                if health and health.hp > 0:
                    available.append(part_type)

        if available:
            gauge_comp.selected_part = random.choice(available)
            gauge_comp.selected_action = "attack"
            
            selected_part_id = part_list_comp.parts.get(gauge_comp.selected_part)
            selected_part_comps = self.world.entities.get(selected_part_id)
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