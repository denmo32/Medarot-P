"""HP表示用アニメーションシステム"""

from core.ecs import System

class HealthAnimationSystem(System):
    """
    HealthComponentのhp（真値）とdisplay_hp（描画用）を同期させる。
    ダメージを受けた際、表示上のHPを少しずつ減らすアニメーションを行う。
    """
    def update(self, dt: float):
        # バトルシーン内の全HPコンポーネントを対象とする
        # (Medabot機体そのものではなく、各パーツエンティティがHealthを持っている)
        for eid, comps in self.world.get_entities_with_components('health'):
            h = comps['health']
            
            if h.display_hp != h.hp:
                # 差分を取得
                diff = h.hp - h.display_hp
                
                # 変化の速さ（1秒間に最大どれだけHPを動かすか、または割合で動かす）
                # ここでは「残りの差分の一定割合」を動かすことで、減り始めが速く、徐々にゆっくりになる演出にする
                lerp_speed = 5.0
                change = diff * lerp_speed * dt
                
                # 変化が非常に小さい場合は直接代入して終了させる
                if abs(change) < 0.1:
                    h.display_hp = float(h.hp)
                else:
                    h.display_hp += change