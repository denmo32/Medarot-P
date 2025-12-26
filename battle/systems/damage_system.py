"""ダメージ処理システム"""

from core.ecs import System

class DamageSystem(System):
    """DamageEventComponentを監視し、実際のHP減算と敗北判定を行う"""

    def update(self, dt: float):
        contexts = self.world.get_entities_with_components('battlecontext')
        if not contexts: return
        context = contexts[0][1]['battlecontext']

        # DamageEventComponentを持つターゲットを探す
        for target_id, comps in self.world.get_entities_with_components('damageevent', 'partlist', 'defeated'):
            event = comps['damageevent']
            
            # 対象パーツのHPを削る
            part_id = comps['partlist'].parts.get(event.target_part)
            if part_id:
                health = self.world.entities[part_id]['health']
                health.hp = max(0, health.hp - event.damage)
                
                # ログ用部位名
                names = {"head": "頭部", "right_arm": "右腕", "left_arm": "左腕", "legs": "脚部"}
                target_name = self.world.entities[target_id]['medal'].nickname
                msg = f"{target_name}の{names.get(event.target_part)}に{event.damage}のダメージ！"
                context.pending_logs.append(msg)

                # 頭部破壊なら機能停止
                if event.target_part == "head" and health.hp <= 0:
                    comps['defeated'].is_defeated = True

            # 処理が終わったらイベントを削除
            self.world.remove_component(target_id, 'damageevent')