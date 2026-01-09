"""ダメージ処理システム"""

from core.ecs import System
from battle.constants import PartType, BattlePhase

class DamageSystem(System):
    """DamageEventComponentを監視し、実際のHP減算、状態異常適用、敗北判定を行う"""

    def update(self, dt: float):
        entities = self.world.get_entities_with_components('battlecontext')
        if not entities: return
        context = entities[0][1]['battlecontext']

        # DamageEventComponentを持つターゲットを探す
        for target_id, comps in self.world.get_entities_with_components('damageevent', 'partlist', 'defeated', 'gauge'):
            event = comps['damageevent']
            
            # 対象パーツのHPを削る
            part_id = comps['partlist'].parts.get(event.target_part)
            if part_id:
                health = self.world.entities[part_id]['health']
                health.hp = max(0, health.hp - event.damage)
                
                # ログ用部位名
                names = {
                    PartType.HEAD: "頭部", 
                    PartType.RIGHT_ARM: "右腕", 
                    PartType.LEFT_ARM: "左腕", 
                    PartType.LEGS: "脚部"
                }
                target_name = self.world.entities[target_id]['medal'].nickname
                
                crit_text = " (クリティカル!)" if event.is_critical else ""
                msg = f"{target_name}の{names.get(event.target_part, '不明な部位')}に{event.damage}のダメージ！{crit_text}"
                
                # 詳細ログは一時保存
                context.pending_logs.append(msg)

                # 状態異常：停止の適用
                if event.stop_duration > 0:
                    comps['gauge'].stop_timer = max(comps['gauge'].stop_timer, event.stop_duration)
                    context.pending_logs.append(f"{target_name}は電撃で動きが止まった！")

                # 頭部破壊なら機能停止
                if event.target_part == PartType.HEAD and health.hp <= 0:
                    comps['defeated'].is_defeated = True

            # 処理が終わったらイベントを削除
            self.world.remove_component(target_id, 'damageevent')