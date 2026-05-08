"""表示専用のシステム群"""

from core.ecs import System

class HealthAnimationSystem(System):
    """
    HealthComponentのhp（真値）とdisplay_hp（描画用）を同期させる。
    ダメージを受けた際、表示上のHPを少しずつ減らすアニメーションを行う。
    ロジックには影響せず、ユーザーインターフェースのためだけに存在する。
    """
    def update(self, dt: float):
        # バトルシーン内の全HPコンポーネントを対象とする
        # (Medabot機体そのものではなく、各パーツエンティティがHealthを持っている)
        for eid, comps in self.world.get_entities_with_components('health'):
            h = comps['health']
            
            if h.display_hp != h.hp:
                # 差分を取得
                diff = h.hp - h.display_hp
                
                # 1秒間で目標値に近づく速さ（時定数の逆数）
                # 指数移動（Exponential Decay）による滑らかな追従
                approach_rate = 5.0
                change = diff * approach_rate * dt
                
                # 誤差が十分に小さければ一気に目標値へ確定させる（微小な振動を避ける）
                if abs(diff) < 0.2:
                    h.display_hp = float(h.hp)
                else:
                    h.display_hp += change
                    # クランプ処理を追加して境界値を守る
                    h.display_hp = max(0.0, min(float(h.max_hp), h.display_hp))