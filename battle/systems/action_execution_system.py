"""行動実行システム"""

import random
from core.ecs import System
from components.battle import DamageEventComponent
from battle.utils import calculate_current_x

class ActionExecutionSystem(System):
    """チャージ完了した行動のメッセージ生成と、ダメージイベントの発行を担当"""

    def update(self, dt: float):
        contexts = self.world.get_entities_with_components('battlecontext')
        if not contexts: return
        context = contexts[0][1]['battlecontext']

        if context.waiting_for_input or context.waiting_for_action or context.game_over:
            return

        if not context.waiting_queue: return
        eid = context.waiting_queue[0]
        
        comps = self.world.entities.get(eid)
        if not comps: return
        
        gauge = comps['gauge']
        if gauge.status == gauge.CHARGING and gauge.progress >= 100.0:
            self._execute(eid, context, comps)
            
            # 実行完了後はクールダウンへ
            gauge.status = gauge.COOLDOWN
            gauge.progress = 0.0
            gauge.selected_action = None
            gauge.selected_part = None
            context.waiting_queue.pop(0)

    def _execute(self, eid, context, comps):
        gauge = comps['gauge']
        attacker_name = comps['medal'].nickname
        
        if gauge.selected_action == "attack":
            part_id = comps['partlist'].parts.get(gauge.selected_part)
            attack_comp = self.world.entities[part_id].get('attack')
            
            # ターゲット決定
            target_id = self._determine_target(eid, comps, attack_comp)
            if not target_id: return

            # ダメージ計算（イベントとしてDamageSystemに渡すための準備）
            damage, target_part = self._prepare_damage(eid, target_id, attack_comp)
            
            # イベント付与
            self.world.add_component(target_id, DamageEventComponent(eid, gauge.selected_part, damage, target_part))

            # ログ出力
            context.battle_log.append(f"{attacker_name}の攻撃！ {attack_comp.trait}！")
            context.execution_target_id = target_id
            context.waiting_for_input = True
            
        elif gauge.selected_action == "skip":
            context.battle_log.append(f"{attacker_name}は行動をスキップ！")
            context.waiting_for_input = True

    def _determine_target(self, eid, comps, attack_comp):
        # 特性や事前選定に基づきターゲットを確定
        target_id = None
        if attack_comp.trait in ["ソード", "ハンマー"]:
            # 直前ターゲット：現在のアイコン座標が最も中央に近い敵を狙う
            target_id = self._get_closest_target(eid, comps['team'].team_type)
        else:
            # 事前ターゲット：性格が選んだ相手
            target_id = comps['gauge'].part_targets.get(comps['gauge'].selected_part)
        
        # 救済措置
        if not target_id or target_id not in self.world.entities or self.world.entities[target_id]['defeated'].is_defeated:
            target_id = self._get_fallback_target(comps['team'].team_type)
        return target_id

    def _prepare_damage(self, attacker_id, target_id, attack_comp):
        target_comps = self.world.entities[target_id]
        alive_parts = [p for p, pid in target_comps['partlist'].parts.items() 
                       if self.world.entities[pid]['health'].hp > 0]
        
        t_part = random.choice(alive_parts) if alive_parts else "head"
        damage = random.randint(int(attack_comp.attack * 0.8), int(attack_comp.attack * 1.2))
        return damage, t_part

    def _get_closest_target(self, eid, my_team):
        """現在のX座標（ゲージ進行度）に基づき、最も「前（中央）」にいる敵を取得"""
        target_team = "enemy" if my_team == "player" else "player"
        
        best_target = None
        # プレイヤーが攻撃する場合、敵のX座標が最小（最も左）のものが一番近い
        # エネミーが攻撃する場合、プレイヤーのX座標が最大（最も右）のものが一番近い
        extreme_x = float('inf') if my_team == "player" else float('-inf')
        
        for teid, tcomps in self.world.get_entities_with_components('team', 'defeated', 'position', 'gauge'):
            if tcomps['team'].team_type == target_team and not tcomps['defeated'].is_defeated:
                # 現在の視覚的なX座標を計算
                cur_x = calculate_current_x(
                    tcomps['position'].x, 
                    tcomps['gauge'].status, 
                    tcomps['gauge'].progress, 
                    tcomps['team'].team_type
                )
                
                if my_team == "player":
                    if cur_x < extreme_x:
                        extreme_x = cur_x
                        best_target = teid
                else:
                    if cur_x > extreme_x:
                        extreme_x = cur_x
                        best_target = teid
                        
        return best_target

    def _get_fallback_target(self, my_team):
        target_team = "enemy" if my_team == "player" else "player"
        alive = [teid for teid, tcomps in self.world.get_entities_with_components('team', 'defeated') 
                 if tcomps['team'].team_type == target_team and not tcomps['defeated'].is_defeated]
        return random.choice(alive) if alive else None